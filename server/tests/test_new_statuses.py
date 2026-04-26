"""Tests for stun, silence, disarm, vulnerable, bleed, marked statuses."""

from __future__ import annotations

import pytest

from agora.application.engine import MatchEngine
from agora.application.ports import CharacterRepository
from agora.application.use_cases import start_match
from agora.domain.character import Character, Effect, Skill
from agora.domain.enums import DamageClass, EffectKind, Essence, SkillKind, TargetKind
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


def _spear_action(achilles_id: str = "achilles") -> Action:
    return Action(
        character_id="achilles",
        skill_id="spear",
        target_ids=[achilles_id],
        paid={Essence.VIGOR: 1},
    )


def test_stunned_character_cannot_act(state: MatchState, engine: MatchEngine) -> None:
    state.a.essences[Essence.VIGOR] = 1
    # Duration 2 because statuses tick (and decrement) at the start of the turn.
    state.a.characters[0].statuses.append(ActiveStatus(name="stun", duration=2))

    new_state, events = engine.resolve_turn(state, [_spear_action()])
    assert any(e.kind == "invalid_action" and e.details.get("reason") == "stunned" for e in events)
    # No damage applied to side B's Achilles.
    assert new_state.b.characters[0].hp == new_state.b.characters[0].hp_max


def test_silenced_blocks_magical_skill_only(
    state: MatchState, engine: MatchEngine
) -> None:
    state.a.essences[Essence.MIND] = 1
    state.a.characters[1].statuses.append(ActiveStatus(name="silence", duration=2))

    spear_of_wisdom = Action(
        character_id="athena",
        skill_id="spear_of_wisdom",
        target_ids=["achilles"],
        paid={Essence.MIND: 1},
    )
    _, events = engine.resolve_turn(state, [spear_of_wisdom])
    assert any(e.kind == "invalid_action" and e.details.get("reason") == "silenced" for e in events)


def test_disarmed_blocks_physical_skill_only(
    state: MatchState, engine: MatchEngine
) -> None:
    state.a.essences[Essence.VIGOR] = 1
    state.a.characters[0].statuses.append(ActiveStatus(name="disarm", duration=2))

    _, events = engine.resolve_turn(state, [_spear_action()])
    assert any(e.kind == "invalid_action" and e.details.get("reason") == "disarmed" for e in events)


def test_disarm_does_not_block_magical(state: MatchState, engine: MatchEngine) -> None:
    state.a.essences[Essence.MIND] = 1
    state.a.characters[1].statuses.append(ActiveStatus(name="disarm", duration=2))

    spear_of_wisdom = Action(
        character_id="athena",
        skill_id="spear_of_wisdom",
        target_ids=["achilles"],
        paid={Essence.MIND: 1},
    )
    new_state, events = engine.resolve_turn(state, [spear_of_wisdom])
    assert any(e.kind == "skill_used" for e in events)
    assert new_state.b.characters[0].hp < new_state.b.characters[0].hp_max


def test_vulnerable_blocks_invulnerable_application(
    state: MatchState, engine: MatchEngine
) -> None:
    state.a.essences[Essence.GENERIC] = 0  # ignore — dodge uses generic
    state.a.essences[Essence.VIGOR] = 1
    state.a.characters[0].statuses.append(ActiveStatus(name="vulnerable", duration=2))

    dodge = Action(
        character_id="achilles",
        skill_id="dodge",
        target_ids=[],
        paid={Essence.VIGOR: 1},
    )
    new_state, events = engine.resolve_turn(state, [dodge])
    achilles_a = new_state.a.characters[0]
    assert all(s.name != "invulnerable" for s in achilles_a.statuses)
    assert any(
        e.kind == "status_expired" and e.details.get("blocked_by") == "vulnerable"
        for e in events
    )


def test_bleed_ticks_damage_at_turn_start(
    state: MatchState, engine: MatchEngine
) -> None:
    target = state.b.characters[0]
    target.statuses.append(ActiveStatus(name="bleed", duration=2, value=8))
    starting_hp = target.hp

    new_state, events = engine.resolve_turn(state, [])
    target = new_state.b.characters[0]
    assert target.hp == starting_hp - 8
    assert any(
        e.kind == "damage" and e.details.get("source") == "bleed" for e in events
    )


def test_marked_adds_flat_damage(state: MatchState, engine: MatchEngine) -> None:
    state.a.essences[Essence.VIGOR] = 1
    state.b.characters[0].statuses.append(ActiveStatus(name="marked", duration=2, value=7))

    new_state, _ = engine.resolve_turn(state, [_spear_action()])
    target = new_state.b.characters[0]
    # Spear is 20; marked adds 7.
    assert target.hp == target.hp_max - 27


def test_marked_with_zero_value_is_just_a_tag(
    state: MatchState, engine: MatchEngine
) -> None:
    state.a.essences[Essence.VIGOR] = 1
    state.b.characters[0].statuses.append(ActiveStatus(name="marked", duration=2, value=0))

    new_state, _ = engine.resolve_turn(state, [_spear_action()])
    target = new_state.b.characters[0]
    assert target.hp == target.hp_max - 20


def test_skill_classification_based_on_damage_class() -> None:
    """Holy/mental skills are immune to silence and disarm."""
    from agora.application.engine.skill_validator import (
        is_skill_magical,
        is_skill_physical,
    )

    holy_skill = Skill(
        id="x", name="X", kind=SkillKind.INSTANT, target=TargetKind.SELF,
        effects=[Effect(kind=EffectKind.DAMAGE, value=10, damage_class=DamageClass.HOLY)],
    )
    assert not is_skill_physical(holy_skill)
    assert not is_skill_magical(holy_skill)


def test_stunned_with_silence_still_uses_correct_reason(
    state: MatchState, engine: MatchEngine
) -> None:
    """When both stun and silence are active, stun is reported first (most blocking)."""
    state.a.essences[Essence.MIND] = 1
    state.a.characters[1].statuses.append(ActiveStatus(name="stun", duration=2))
    state.a.characters[1].statuses.append(ActiveStatus(name="silence", duration=2))

    spear_of_wisdom = Action(
        character_id="athena",
        skill_id="spear_of_wisdom",
        target_ids=["achilles"],
        paid={Essence.MIND: 1},
    )
    _, events = engine.resolve_turn(state, [spear_of_wisdom])
    invalid = next(e for e in events if e.kind == "invalid_action")
    assert invalid.details.get("reason") == "stunned"
