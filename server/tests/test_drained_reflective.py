"""Tests for the `drained` status tick and the `reflective` damage behavior."""

from __future__ import annotations

import pytest

from agora.application.engine import MatchEngine
from agora.application.ports import CharacterRepository
from agora.domain.character import Character
from agora.domain.enums import Essence
from agora.domain.match import Action, ActiveStatus, MatchState
from agora.infrastructure.seeded_random import SeededRandom


@pytest.fixture
def engine(repository: CharacterRepository) -> MatchEngine:
    return MatchEngine(characters=repository, rng=SeededRandom(42))


@pytest.fixture
def state(
    engine: MatchEngine, all_characters: dict[str, Character]
) -> MatchState:
    return engine.start_match(
        match_id="m1",
        player_a_id="p1",
        team_a=[all_characters["achilles"], all_characters["athena"], all_characters["anubis"]],
        player_b_id="p2",
        team_b=[all_characters["achilles"], all_characters["athena"], all_characters["anubis"]],
        seed=42,
    )


def test_drained_status_consumes_one_essence_per_turn(
    state: MatchState, engine: MatchEngine
) -> None:
    # Side A is drained. Pre-load known essences so we can assert the drop.
    state.a.essences = {Essence.VIGOR: 2, Essence.MIND: 1, Essence.SPIRIT: 0, Essence.BLOOD: 0}
    state.a.characters[0].statuses.append(ActiveStatus(name="drained", duration=2))

    new_state, events = engine.resolve_turn(state, [])
    after = sum(new_state.a.essences.values())
    # Original 3 essences - 1 drained.
    # (Side A's turn rolled 0 new essences because we only count via the bot,
    # and resolve_turn rolls essences for the *next* active side, not this one.)
    assert after == 2
    assert any(
        e.kind == "essence_drained"
        and e.details.get("source") == "drained_status"
        for e in events
    )


def test_reflective_bounces_first_damage_back_to_caster(
    state: MatchState, engine: MatchEngine
) -> None:
    # Side B's Achilles becomes reflective for 2 turns.
    state.b.characters[0].statuses.append(ActiveStatus(name="reflective", duration=2))

    state.a.essences[Essence.VIGOR] = 1
    spear = Action(
        character_id="achilles",
        skill_id="spear",
        target_ids=["achilles"],  # aim at side B's Achilles
        paid={Essence.VIGOR: 1},
    )
    new_state, events = engine.resolve_turn(state, [spear])

    target_b = new_state.b.characters[0]
    source_a = new_state.a.characters[0]
    # B took no damage (reflected); A took its own 20.
    assert target_b.hp == target_b.hp_max
    assert source_a.hp == source_a.hp_max - 20
    # Status was consumed.
    assert all(s.name != "reflective" for s in target_b.statuses)
    assert any(
        e.kind == "status_expired"
        and e.details.get("status") == "reflective"
        and e.details.get("consumed")
        for e in events
    )


def test_reflective_with_true_effect_passes_through(
    repository: CharacterRepository, all_characters: dict[str, Character]
) -> None:
    """If the incoming damage carries `effect.true`, reflect is bypassed and the target eats it."""
    engine = MatchEngine(characters=repository, rng=SeededRandom(7))
    state = engine.start_match(
        match_id="m2",
        player_a_id="pA",
        team_a=[all_characters["mulan"], all_characters["athena"], all_characters["anubis"]],
        player_b_id="pB",
        team_b=[all_characters["achilles"], all_characters["athena"], all_characters["anubis"]],
        seed=7,
    )
    state.b.characters[0].statuses.append(ActiveStatus(name="reflective", duration=2))
    state.a.essences[Essence.VIGOR] = 2
    state.a.essences[Essence.GENERIC] = 0  # ignore — paid in vigor as generic
    # Mulan's family_honor is cost { vigor: 2, generic: 1 } — pay generic in vigor.
    state.a.essences[Essence.VIGOR] = 3

    family_honor = Action(
        character_id="mulan",
        skill_id="family_honor",
        target_ids=["achilles"],
        paid={Essence.VIGOR: 3},
    )
    new_state, _ = engine.resolve_turn(state, [family_honor])
    target_b = new_state.b.characters[0]
    # Reflective was bypassed; target took the hit (40 piercing+true).
    assert target_b.hp <= target_b.hp_max - 40
    # Status NOT consumed because the damage was inevitable.
    assert any(s.name == "reflective" for s in target_b.statuses)


def test_loki_asgard_deceit_yaml_grants_reflective(
    repository: CharacterRepository, all_characters: dict[str, Character]
) -> None:
    """The YAML kit ships the reflective hook on Loki's third skill.

    Loads Loki from the real YAML, casts `asgard_deceit`, then has the
    enemy throw a basic damage skill at him — it should bounce.
    """
    engine = MatchEngine(characters=repository, rng=SeededRandom(11))
    state = engine.start_match(
        match_id="m3",
        player_a_id="pA",
        team_a=[all_characters["loki"], all_characters["athena"], all_characters["anubis"]],
        player_b_id="pB",
        team_b=[all_characters["achilles"], all_characters["athena"], all_characters["anubis"]],
        seed=11,
    )

    # Loki casts Asgard's Deceit on himself; cost is mind:2 + generic:1 = 3 total.
    state.a.essences[Essence.MIND] = 3
    deceit = Action(
        character_id="loki",
        skill_id="asgard_deceit",
        target_ids=["loki"],
        paid={Essence.MIND: 3},
    )
    state, _ = engine.resolve_turn(state, [deceit])
    loki = state.a.characters[0]
    assert any(s.name == "reflective" for s in loki.statuses)

    # B's turn now. Achilles spears Loki — it should bounce.
    state.b.essences[Essence.VIGOR] = 1
    spear = Action(
        character_id="achilles",
        skill_id="spear",
        target_ids=["loki"],
        paid={Essence.VIGOR: 1},
    )
    state, events = engine.resolve_turn(state, [spear])
    loki = state.a.characters[0]
    achilles_b = state.b.characters[0]

    # Loki untouched, Achilles ate his own spear.
    assert loki.hp == loki.hp_max
    assert achilles_b.hp == achilles_b.hp_max - 20
    assert any(
        e.kind == "status_expired"
        and e.details.get("status") == "reflective"
        and e.details.get("consumed")
        for e in events
    )
