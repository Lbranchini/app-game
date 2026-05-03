"""Stealth status: untargetable until the bearer commits an offensive action."""

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
    return MatchEngine(characters=repository, rng=SeededRandom(7))


@pytest.fixture
def state(
    engine: MatchEngine, all_characters: dict[str, Character]
) -> MatchState:
    """Achilles+Athena+Mulan vs Achilles+Athena+Anubis. Side B starts."""
    return engine.start_match(
        match_id="m",
        player_a_id="a",
        team_a=[all_characters["achilles"], all_characters["athena"], all_characters["mulan"]],
        player_b_id="b",
        team_b=[all_characters["achilles"], all_characters["athena"], all_characters["anubis"]],
        seed=7,
    )


def test_single_target_skill_against_stealthed_enemy_is_invalid(
    state: MatchState, engine: MatchEngine
) -> None:
    """B's Achilles tries to spear A's Mulan, who is stealthed → invalid_action."""
    # Force B's turn so they're the active side.
    if state.current_side.value == "A":
        state, _ = engine.resolve_turn(state, [])

    state.a.characters[2].statuses.append(ActiveStatus(name="stealth", duration=2))
    state.b.essences[Essence.VIGOR] = 1

    spear = Action(
        character_id="achilles",
        skill_id="spear",
        target_ids=["mulan"],
        paid={Essence.VIGOR: 1},
    )
    new_state, events = engine.resolve_turn(state, [spear])

    mulan = new_state.a.characters[2]
    assert mulan.hp == mulan.hp_max  # untouched
    assert any(
        e.kind == "invalid_action" and e.details.get("reason") == "target_stealthed"
        for e in events
    )
    # The cost was not charged either — stealth check rejected before payment.
    assert new_state.b.essences.get(Essence.VIGOR, 0) == 1


def test_aoe_skill_skips_stealthed_enemies(
    repository: CharacterRepository, all_characters: dict[str, Character]
) -> None:
    """Thor's all_enemies lightning leaves a stealthed Mulan untouched while
    hitting the rest of her team."""
    engine = MatchEngine(characters=repository, rng=SeededRandom(11))
    state = engine.start_match(
        match_id="m_aoe",
        player_a_id="a",
        team_a=[
            all_characters["achilles"],
            all_characters["athena"],
            all_characters["mulan"],
        ],
        player_b_id="b",
        team_b=[
            all_characters["thor"],
            all_characters["athena"],
            all_characters["anubis"],
        ],
        seed=11,
    )
    # Force B to be active.
    if state.current_side.value == "A":
        state, _ = engine.resolve_turn(state, [])

    state.a.characters[2].statuses.append(ActiveStatus(name="stealth", duration=2))

    # Thor's `lightning_strike` is all_enemies. Pay its cost out of B's pool.
    thor_def = all_characters["thor"]
    skill = next(s for s in thor_def.skills if s.target.value == "all_enemies")
    state.b.essences = {Essence.VIGOR: 0, Essence.SPIRIT: 0, Essence.MIND: 0, Essence.BLOOD: 0}
    for k, v in skill.cost.items():
        if k is not Essence.GENERIC:
            state.b.essences[k] = state.b.essences.get(k, 0) + v
    if Essence.GENERIC in skill.cost:
        # Pay generic out of vigor.
        state.b.essences[Essence.VIGOR] = (
            state.b.essences.get(Essence.VIGOR, 0) + skill.cost[Essence.GENERIC]
        )
    paid: dict[Essence, int] = {}
    for k, v in skill.cost.items():
        if k is Essence.GENERIC:
            paid[Essence.VIGOR] = paid.get(Essence.VIGOR, 0) + v
        else:
            paid[k] = v

    aoe = Action(
        character_id="thor",
        skill_id=skill.id,
        target_ids=[],
        paid=paid,
    )
    new_state, _ = engine.resolve_turn(state, [aoe])

    achilles_a = new_state.a.characters[0]
    mulan = new_state.a.characters[2]
    # Achilles ate damage; Mulan was stealthed and was filtered out of the AoE.
    assert achilles_a.hp < achilles_a.hp_max
    assert mulan.hp == mulan.hp_max


def test_stealth_breaks_when_bearer_attacks(
    state: MatchState, engine: MatchEngine
) -> None:
    """A stealthed Mulan loses the status the moment she uses an offensive skill."""
    state.a.characters[2].statuses.append(ActiveStatus(name="stealth", duration=3))
    state.a.essences[Essence.VIGOR] = 1

    sword = Action(
        character_id="mulan",
        skill_id="hidden_sword",
        target_ids=["achilles"],
        paid={Essence.VIGOR: 1},
    )
    new_state, events = engine.resolve_turn(state, [sword])

    mulan = new_state.a.characters[2]
    assert all(s.name != "stealth" for s in mulan.statuses)
    assert any(
        e.kind == "status_expired"
        and e.details.get("status") == "stealth"
        and e.details.get("consumed")
        for e in events
    )


def test_stealth_survives_self_or_ally_skill(
    state: MatchState, engine: MatchEngine
) -> None:
    """A defensive skill (target=self/ally) does not break stealth."""
    state.a.characters[1].statuses.append(ActiveStatus(name="stealth", duration=3))
    state.a.essences[Essence.SPIRIT] = 1
    state.a.essences[Essence.GENERIC] = 0

    # Athena's `aegis` is all_allies — explicitly non-offensive.
    aegis = Action(
        character_id="athena",
        skill_id="aegis",
        target_ids=[],
        paid={Essence.SPIRIT: 1},
    )
    new_state, _ = engine.resolve_turn(state, [aegis])

    athena = new_state.a.characters[1]
    assert any(s.name == "stealth" for s in athena.statuses)


def test_disguise_yaml_grants_stealth(
    state: MatchState, engine: MatchEngine
) -> None:
    """Mulan's `disguise` from YAML actually attaches the stealth status."""
    state.a.essences[Essence.VIGOR] = 2  # 1 vigor + 1 generic paid in vigor

    disguise = Action(
        character_id="mulan",
        skill_id="disguise",
        target_ids=["mulan"],
        paid={Essence.VIGOR: 2},
    )
    new_state, events = engine.resolve_turn(state, [disguise])
    mulan = new_state.a.characters[2]
    assert any(s.name == "stealth" for s in mulan.statuses)
    assert any(s.name == "damage_buff" for s in mulan.statuses)
    assert any(
        e.kind == "status_applied" and e.details.get("status") == "stealth"
        for e in events
    )


def test_stealth_ticks_down_each_turn(
    state: MatchState, engine: MatchEngine
) -> None:
    """Stealth duration decrements like any other status."""
    state.a.characters[2].statuses.append(ActiveStatus(name="stealth", duration=2))

    new_state, _ = engine.resolve_turn(state, [])  # A's turn
    new_state, _ = engine.resolve_turn(new_state, [])  # B's turn
    # Two turn ends elapsed; stealth duration started at 2.
    new_state, _ = engine.resolve_turn(new_state, [])  # A's turn again

    mulan = new_state.a.characters[2]
    assert all(s.name != "stealth" for s in mulan.statuses)


def test_remove_afflictions_does_not_strip_stealth(
    state: MatchState, engine: MatchEngine
) -> None:
    """Stealth is a self-buff, so cleanses must leave it alone."""
    from agora.application.engine.context import EffectContext
    from agora.application.engine.effect_handlers import RemoveAfflictionsHandler
    from agora.domain.character import Effect
    from agora.domain.enums import EffectKind

    target = state.a.characters[2]
    target.statuses.append(ActiveStatus(name="stealth", duration=2))
    target.statuses.append(ActiveStatus(name="poison", duration=2, value=5))

    events = []
    RemoveAfflictionsHandler().apply(
        Effect(kind=EffectKind.REMOVE_AFFLICTIONS, value=0),
        EffectContext(
            state=state,
            source=target,
            target=target,
            target_owner=state.a,
            rng=SeededRandom(0),
            events=events,
        ),
    )
    assert any(s.name == "stealth" for s in target.statuses)
    assert all(s.name != "poison" for s in target.statuses)
