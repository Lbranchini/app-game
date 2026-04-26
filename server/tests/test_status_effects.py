"""Tests for status effects: poison, damage reduction, shield, buff, piercing."""

from __future__ import annotations

import pytest

from agora.application.ports import CharacterRepository, RandomSource
from agora.application.use_cases import resolve_turn, start_match
from agora.domain.character import Character
from agora.domain.enums import Essence
from agora.domain.match import Action, MatchState
from agora.infrastructure.seeded_random import SeededRandom


@pytest.fixture
def rng() -> RandomSource:
    return SeededRandom(42)


@pytest.fixture
def state(
    repository: CharacterRepository,
    all_characters: dict[str, Character],
    rng: RandomSource,
) -> MatchState:
    achilles = all_characters["achilles"]
    athena = all_characters["athena"]
    anubis = all_characters["anubis"]
    return start_match(
        match_id="m1",
        player_a_id="p1",
        team_a=[achilles, athena, anubis],
        player_b_id="p2",
        team_b=[achilles, athena, anubis],
        rng=rng,
        seed=42,
    )


def test_poison_ticks_at_turn_start(
    state: MatchState, repository: CharacterRepository, rng: RandomSource
) -> None:
    # Anubis (A) hits Achilles (B) with Choking Wraps -> 10 dmg + poison 10 for 2 turns.
    state.a.essences[Essence.BLOOD] = 1
    action = Action(
        character_id="anubis",
        skill_id="wraps",
        target_ids=["achilles"],
        paid={Essence.BLOOD: 1},
    )
    state, _ = resolve_turn(state, [action], repository, rng)

    target = state.b.characters[0]
    assert target.hp == target.hp_max - 10
    assert any(s.name == "poison" for s in target.statuses)

    # Side B's turn: status tick at start applies 10 more poison damage.
    state, _ = resolve_turn(state, [], repository, rng)
    assert state.b.characters[0].hp == target.hp_max - 20


def test_poison_expires_after_duration(
    state: MatchState, repository: CharacterRepository, rng: RandomSource
) -> None:
    state.a.essences[Essence.BLOOD] = 1
    action = Action(
        character_id="anubis",
        skill_id="wraps",
        target_ids=["achilles"],
        paid={Essence.BLOOD: 1},
    )
    state, _ = resolve_turn(state, [action], repository, rng)
    state, _ = resolve_turn(state, [], repository, rng)
    state, _ = resolve_turn(state, [], repository, rng)
    target = state.b.characters[0]
    assert all(s.name != "poison" for s in target.statuses)


def test_damage_reduction_applies_to_incoming_damage(
    state: MatchState, repository: CharacterRepository, rng: RandomSource
) -> None:
    state.a.essences[Essence.MIND] = 1
    state.a.essences[Essence.VIGOR] = 1  # used as generic
    counsel = Action(
        character_id="athena",
        skill_id="counsel",
        target_ids=["achilles"],
        paid={Essence.MIND: 1, Essence.VIGOR: 1},
    )
    state, _ = resolve_turn(state, [counsel], repository, rng)

    state.b.essences[Essence.VIGOR] = 1
    spear = Action(
        character_id="achilles",
        skill_id="spear",
        target_ids=["achilles"],
        paid={Essence.VIGOR: 1},
    )
    state, _ = resolve_turn(state, [spear], repository, rng)

    achilles_a = state.a.characters[0]
    # 20 - 15 reduction = 5
    assert achilles_a.hp == achilles_a.hp_max - 5


def test_destructible_shield_absorbs_before_hp(
    state: MatchState, repository: CharacterRepository, rng: RandomSource
) -> None:
    state.a.essences[Essence.MIND] = 2
    state.a.essences[Essence.VIGOR] = 2
    aegis = Action(
        character_id="athena",
        skill_id="aegis",
        target_ids=[],
        paid={Essence.MIND: 2, Essence.VIGOR: 2},
    )
    state, _ = resolve_turn(state, [aegis], repository, rng)

    achilles_a = state.a.characters[0]
    assert achilles_a.shield == 25

    state.b.essences[Essence.VIGOR] = 1
    spear = Action(
        character_id="achilles",
        skill_id="spear",
        target_ids=["achilles"],
        paid={Essence.VIGOR: 1},
    )
    state, _ = resolve_turn(state, [spear], repository, rng)
    achilles_a = state.a.characters[0]
    # 20 dmg fully absorbed; shield drops 25 -> 5; hp untouched.
    assert achilles_a.shield == 5
    assert achilles_a.hp == achilles_a.hp_max


def test_damage_buff_adds_to_outgoing_damage(
    state: MatchState, repository: CharacterRepository, rng: RandomSource
) -> None:
    state.a.essences[Essence.VIGOR] = 3
    state.a.essences[Essence.MIND] = 1
    wrath = Action(
        character_id="achilles",
        skill_id="wrath",
        target_ids=[],
        paid={Essence.VIGOR: 2, Essence.MIND: 1},
    )
    state, _ = resolve_turn(state, [wrath], repository, rng)
    state, _ = resolve_turn(state, [], repository, rng)

    state.a.essences[Essence.VIGOR] = 1
    spear = Action(
        character_id="achilles",
        skill_id="spear",
        target_ids=["achilles"],
        paid={Essence.VIGOR: 1},
    )
    state, _ = resolve_turn(state, [spear], repository, rng)
    achilles_b = state.b.characters[0]
    # 20 (spear) + 15 (damage_buff) = 35
    assert achilles_b.hp == achilles_b.hp_max - 35


def test_piercing_ignores_damage_reduction(
    state: MatchState, repository: CharacterRepository, rng: RandomSource
) -> None:
    state.b.essences[Essence.MIND] = 1
    state.b.essences[Essence.VIGOR] = 1
    state, _ = resolve_turn(state, [], repository, rng)

    counsel = Action(
        character_id="athena",
        skill_id="counsel",
        target_ids=["achilles"],
        paid={Essence.MIND: 1, Essence.VIGOR: 1},
    )
    state, _ = resolve_turn(state, [counsel], repository, rng)

    state.a.essences[Essence.BLOOD] = 2
    state.a.essences[Essence.MIND] = 1
    burden = Action(
        character_id="anubis",
        skill_id="heart_burden",
        target_ids=["achilles"],
        paid={Essence.BLOOD: 2, Essence.MIND: 1},
    )
    state, _ = resolve_turn(state, [burden], repository, rng)
    achilles_b = state.b.characters[0]
    # 30 piercing — ignores the 15 damage_reduction.
    assert achilles_b.hp == achilles_b.hp_max - 30
