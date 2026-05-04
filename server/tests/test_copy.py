"""`copy` mechanic — Loki's third archetype lever.

The copy effect lets the source borrow a target's most-recently-used
skill into `granted_skills` for `effect.duration` of the source's
turns. The borrowed skill is usable as if it were the source's own
(paying its cost from the source's pool, rolling its own cooldown),
and it disappears at the end of the bearer's turn when its
`turns_remaining` hits zero.
"""

from __future__ import annotations

import pytest

from agora.application.engine import MatchEngine
from agora.application.engine.context import EffectContext
from agora.application.engine.effect_handlers import CopyHandler
from agora.application.ports import CharacterRepository
from agora.domain.character import Character, Effect
from agora.domain.enums import EffectKind, Essence
from agora.domain.match import Action, GrantedSkill, MatchState
from agora.infrastructure.seeded_random import SeededRandom


@pytest.fixture
def engine(repository: CharacterRepository) -> MatchEngine:
    return MatchEngine(characters=repository, rng=SeededRandom(11))


@pytest.fixture
def state(
    engine: MatchEngine, all_characters: dict[str, Character]
) -> MatchState:
    """Loki team (A) vs Achilles team (B). Side A acts first by default."""
    return engine.start_match(
        match_id="m_copy",
        player_a_id="a",
        team_a=[all_characters["loki"], all_characters["athena"], all_characters["anubis"]],
        player_b_id="b",
        team_b=[all_characters["achilles"], all_characters["athena"], all_characters["anubis"]],
        seed=11,
    )


# --------------------------------------------------------------------------- #
# Handler unit tests                                                          #
# --------------------------------------------------------------------------- #


def test_copy_handler_grants_targets_last_skill(state: MatchState) -> None:
    """Direct handler call: target had a `last_skill_id`, source gets a copy."""
    loki = state.a.characters[0]
    achilles_b = state.b.characters[0]
    achilles_b.last_skill_id = "spear"

    events = []
    CopyHandler().apply(
        Effect(kind=EffectKind.COPY, duration=2),
        EffectContext(
            state=state,
            source=loki,
            target=achilles_b,
            target_owner=state.b,
            rng=SeededRandom(0),
            events=events,
        ),
    )
    assert len(loki.granted_skills) == 1
    assert loki.granted_skills[0].skill_id == "spear"
    assert loki.granted_skills[0].source_character_id == "achilles"
    assert loki.granted_skills[0].turns_remaining == 2
    assert any(
        e.kind == "skill_granted"
        and e.details.get("skill") == "spear"
        and e.details.get("from") == "achilles"
        for e in events
    )


def test_copy_handler_noop_when_target_has_no_last_skill(state: MatchState) -> None:
    loki = state.a.characters[0]
    achilles_b = state.b.characters[0]
    assert achilles_b.last_skill_id is None  # default

    events = []
    CopyHandler().apply(
        Effect(kind=EffectKind.COPY, duration=2),
        EffectContext(
            state=state,
            source=loki,
            target=achilles_b,
            target_owner=state.b,
            rng=SeededRandom(0),
            events=events,
        ),
    )
    assert loki.granted_skills == []
    assert any(
        e.kind == "invalid_action"
        and e.details.get("reason") == "copy_no_target_skill"
        for e in events
    )


def test_copy_refresh_does_not_stack_same_skill(state: MatchState) -> None:
    """Re-casting copy on the same target should refresh the duration, not
    pile up duplicate entries."""
    loki = state.a.characters[0]
    achilles_b = state.b.characters[0]
    achilles_b.last_skill_id = "spear"

    for _ in range(3):
        CopyHandler().apply(
            Effect(kind=EffectKind.COPY, duration=2),
            EffectContext(
                state=state,
                source=loki,
                target=achilles_b,
                target_owner=state.b,
                rng=SeededRandom(0),
                events=[],
            ),
        )
    spear_grants = [g for g in loki.granted_skills if g.skill_id == "spear"]
    assert len(spear_grants) == 1
    assert spear_grants[0].turns_remaining == 2  # refreshed, not stacked


# --------------------------------------------------------------------------- #
# Engine integration tests                                                    #
# --------------------------------------------------------------------------- #


def test_engine_records_last_skill_id_on_offensive_resolve(
    state: MatchState, engine: MatchEngine
) -> None:
    """A non-self skill use sets `actor.last_skill_id` so a future copy can read it."""
    if state.current_side.value == "A":
        state, _ = engine.resolve_turn(state, [])  # hand the turn to B

    state.b.essences[Essence.VIGOR] = 1
    spear = Action(
        character_id="achilles",
        skill_id="spear",
        target_ids=["loki"],
        paid={Essence.VIGOR: 1},
    )
    state, _ = engine.resolve_turn(state, [spear])
    achilles_b = state.b.characters[0]
    assert achilles_b.last_skill_id == "spear"


def test_self_skill_does_not_overwrite_last_skill_id(
    state: MatchState, engine: MatchEngine
) -> None:
    """Buffs aimed at self are awkward to copy back at the buffer; we leave
    `last_skill_id` untouched on a self-target resolve."""
    achilles_b = state.b.characters[0]
    achilles_b.last_skill_id = "spear"  # pretend they speared earlier

    if state.current_side.value == "A":
        state, _ = engine.resolve_turn(state, [])

    state.b.essences[Essence.VIGOR] = 1
    state.b.essences[Essence.GENERIC] = 0
    # Achilles's `divine_armor` is a self target.
    armor = Action(
        character_id="achilles",
        skill_id="divine_armor",
        target_ids=["achilles"],
        paid={Essence.VIGOR: 1},
    )
    new_state, _ = engine.resolve_turn(state, [armor])
    assert new_state.b.characters[0].last_skill_id == "spear"


def test_loki_can_use_a_granted_skill(
    state: MatchState, engine: MatchEngine
) -> None:
    """End-to-end: B's Achilles gains a `last_skill_id`, A's Loki copies and
    uses it the same turn, the engine treats the granted skill as legal."""
    if state.current_side.value == "A":
        state, _ = engine.resolve_turn(state, [])

    # B uses spear so its last_skill_id sticks for A's next turn.
    state.b.essences[Essence.VIGOR] = 1
    state, _ = engine.resolve_turn(
        state,
        [
            Action(
                character_id="achilles",
                skill_id="spear",
                target_ids=["loki"],
                paid={Essence.VIGOR: 1},
            )
        ],
    )
    achilles_b = state.b.characters[0]
    assert achilles_b.last_skill_id == "spear"

    # A's turn: Loki copies spear, then immediately uses the copy on B's
    # Anubis. Loki pays the spear cost (1 vigor) from his own pool.
    state.a.essences[Essence.VIGOR] = 1
    state.a.essences[Essence.MIND] = 1
    state.a.essences[Essence.GENERIC] = 0
    # mirror_image cost is mind:1 + generic:1 — pay generic in mind.
    state.a.essences[Essence.MIND] = 2

    new_state, events = engine.resolve_turn(
        state,
        [
            Action(
                character_id="loki",
                skill_id="mirror_image",
                target_ids=["achilles"],
                paid={Essence.MIND: 2},
            ),
            Action(
                character_id="loki",
                skill_id="spear",
                target_ids=["anubis"],
                paid={Essence.VIGOR: 1},
            ),
        ],
    )
    anubis_b = new_state.b.characters[2]
    assert anubis_b.hp < anubis_b.hp_max  # ate the copied spear
    assert any(
        e.kind == "skill_granted" and e.details.get("skill") == "spear"
        for e in events
    )
    # Both actions resolved successfully — no `invalid_action` for the copy.
    assert not any(
        e.kind == "invalid_action" and e.details.get("skill") == "spear"
        for e in events
    )


def test_granted_skill_expires_after_duration(
    state: MatchState, engine: MatchEngine
) -> None:
    """A granted skill with turns_remaining=2 ticks down at end of bearer's
    turn and is gone after one full Loki turn cycle."""
    loki = state.a.characters[0]
    loki.granted_skills.append(
        GrantedSkill(skill_id="spear", source_character_id="achilles", turns_remaining=2)
    )

    if state.current_side.value == "B":
        state, _ = engine.resolve_turn(state, [])  # advance to A
    # End of A's turn — one tick. Should still have the granted skill.
    state, _ = engine.resolve_turn(state, [])
    assert any(g.skill_id == "spear" for g in state.a.characters[0].granted_skills)

    # B's turn — granted skills don't tick on the opponent.
    state, _ = engine.resolve_turn(state, [])
    assert any(g.skill_id == "spear" for g in state.a.characters[0].granted_skills)

    # A's next turn — second tick. Skill expires.
    new_state, events = engine.resolve_turn(state, [])
    assert all(g.skill_id != "spear" for g in new_state.a.characters[0].granted_skills)
    assert any(
        e.kind == "skill_expired" and e.details.get("skill") == "spear"
        for e in events
    )


def test_granted_skill_cooldown_is_dropped_on_expiry(
    state: MatchState, engine: MatchEngine
) -> None:
    """If Loki used the copied skill (so it left a CD), the CD entry should
    disappear when the granted skill itself expires — no ghost cooldown."""
    loki = state.a.characters[0]
    loki.granted_skills.append(
        GrantedSkill(skill_id="charge", source_character_id="achilles", turns_remaining=1)
    )
    loki.cooldowns["charge"] = 3

    if state.current_side.value == "B":
        state, _ = engine.resolve_turn(state, [])

    new_state, _ = engine.resolve_turn(state, [])  # tick on A's turn end
    loki_after = new_state.a.characters[0]
    assert all(g.skill_id != "charge" for g in loki_after.granted_skills)
    assert "charge" not in loki_after.cooldowns


def test_loki_yaml_mirror_image_grants_copy_handler(
    state: MatchState, engine: MatchEngine, all_characters: dict[str, Character]
) -> None:
    """The shipped Loki kit actually triggers the copy handler — guards
    against accidentally gutting the YAML in a future content pass."""
    loki_def = all_characters["loki"]
    mirror = next(s for s in loki_def.skills if s.id == "mirror_image")
    assert any(e.kind is EffectKind.COPY for e in mirror.effects)
    assert mirror.target.value == "single_enemy"
