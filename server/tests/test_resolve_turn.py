"""Tests for the resolve_turn use case: damage, costs, cooldowns, targeting."""

from __future__ import annotations

import pytest

from agora.application.ports import CharacterRepository, RandomSource
from agora.application.use_cases import resolve_turn, start_match
from agora.domain.character import Character
from agora.domain.enums import Essence, Side
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


def test_match_starts_with_initial_essences(state: MatchState) -> None:
    assert sum(state.a.essences.values()) == 1, "Side A starts with 1 essence"
    assert sum(state.b.essences.values()) == 3, "Side B starts with 3 essences"
    for character in state.a.characters:
        assert character.hp == character.hp_max


def test_spear_deals_20_damage(
    state: MatchState, repository: CharacterRepository, rng: RandomSource
) -> None:
    state.a.essences[Essence.VIGOR] = 1
    for e in (Essence.MIND, Essence.SPIRIT, Essence.BLOOD):
        state.a.essences[e] = 0

    action = Action(
        character_id="achilles",
        skill_id="spear",
        target_ids=["achilles"],
        paid={Essence.VIGOR: 1},
    )
    new_state, events = resolve_turn(state, [action], repository, rng)

    target = new_state.b.characters[0]
    assert target.hp == target.hp_max - 20
    assert any(e.kind == "damage" and e.details.get("value") == 20 for e in events)


def test_insufficient_essence_invalid_action(
    state: MatchState, repository: CharacterRepository, rng: RandomSource
) -> None:
    for e in (Essence.VIGOR, Essence.MIND, Essence.SPIRIT, Essence.BLOOD):
        state.a.essences[e] = 0

    action = Action(
        character_id="achilles",
        skill_id="spear",
        target_ids=["achilles"],
        paid={Essence.VIGOR: 1},
    )
    _, events = resolve_turn(state, [action], repository, rng)
    assert any(
        e.kind == "invalid_action" and e.details.get("reason") == "insufficient_essence"
        for e in events
    )


def test_cooldown_set_then_decrements(
    state: MatchState, repository: CharacterRepository, rng: RandomSource
) -> None:
    state.a.essences[Essence.VIGOR] = 2

    action = Action(
        character_id="achilles",
        skill_id="charge",
        target_ids=["achilles"],
        paid={Essence.VIGOR: 2},
    )
    new_state, _ = resolve_turn(state, [action], repository, rng)

    achilles_state = new_state.a.characters[0]
    # Cooldown was 2; the active turn already decremented once -> 1 left.
    assert achilles_state.cooldowns.get("charge") == 1


def test_side_alternates_each_turn(
    state: MatchState, repository: CharacterRepository, rng: RandomSource
) -> None:
    after_one, _ = resolve_turn(state, [], repository, rng)
    assert after_one.current_side is Side.B
    after_two, _ = resolve_turn(after_one, [], repository, rng)
    assert after_two.current_side is Side.A


def test_invalid_target_does_not_apply_effect(
    state: MatchState, repository: CharacterRepository, rng: RandomSource
) -> None:
    state.a.essences[Essence.VIGOR] = 1

    action = Action(
        character_id="achilles",
        skill_id="spear",
        target_ids=["nonexistent"],
        paid={Essence.VIGOR: 1},
    )
    new_state, _ = resolve_turn(state, [action], repository, rng)
    for character in new_state.b.characters:
        assert character.hp == character.hp_max
