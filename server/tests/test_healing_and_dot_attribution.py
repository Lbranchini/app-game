"""Tests for heal-event attribution and DoT/HoT telemetry credit."""

from __future__ import annotations

from agora.application.engine import MatchEngine
from agora.application.engine.context import EffectContext, StatusTickContext
from agora.application.engine.effect_handlers import HealHandler
from agora.application.engine.status_ticks import (
    BleedTick,
    PoisonTick,
    RegenTick,
)
from agora.application.ports import CharacterRepository
from agora.application.use_cases.match_summary import summarize_events
from agora.domain.character import Character, Effect
from agora.domain.enums import EffectKind
from agora.domain.events import Event
from agora.domain.match import ActiveStatus, CharacterState, MatchState
from agora.infrastructure.seeded_random import SeededRandom


# --------------------------------------------------------------------------- #
# Direct heal carries source                                                  #
# --------------------------------------------------------------------------- #


def _new_state_for_heal(
    repository: CharacterRepository,
    chars: dict[str, Character],
) -> MatchState:
    engine = MatchEngine(characters=repository, rng=SeededRandom(1))
    return engine.start_match(
        match_id="m",
        player_a_id="pA",
        team_a=[chars["isis"], chars["athena"], chars["anubis"]],
        player_b_id="pB",
        team_b=[chars["achilles"], chars["athena"], chars["anubis"]],
        seed=1,
    )


def test_heal_event_carries_source(
    repository: CharacterRepository, all_characters: dict[str, Character]
) -> None:
    state = _new_state_for_heal(repository, all_characters)
    isis = state.a.characters[0]
    athena = state.a.characters[1]
    athena.hp = 50  # leave headroom for the heal

    events: list[Event] = []
    HealHandler().apply(
        Effect(kind=EffectKind.HEAL, value=15),
        EffectContext(
            state=state,
            source=isis,
            target=athena,
            target_owner=state.a,
            rng=SeededRandom(0),
            events=events,
        ),
    )
    heal = next(e for e in events if e.kind == "heal")
    assert heal.details.get("source") == "isis"
    assert heal.details.get("target") == "athena"
    assert heal.details.get("value") == 15


# --------------------------------------------------------------------------- #
# Tick attribution                                                            #
# --------------------------------------------------------------------------- #


def _ticking_character() -> CharacterState:
    return CharacterState(id="achilles", name="Achilles", hp=100, hp_max=100)


def test_poison_tick_credits_status_source() -> None:
    target = _ticking_character()
    status = ActiveStatus(name="poison", duration=2, value=10, source="anubis")

    events: list[Event] = []
    ctx = StatusTickContext(
        status=status,
        character=target,
        player=None,  # type: ignore[arg-type]
        rng=SeededRandom(0),
        events=events,
    )
    PoisonTick().tick(ctx)
    assert events[0].details["source"] == "anubis"
    assert events[0].details["tick"] == "poison"


def test_regen_tick_credits_status_source() -> None:
    target = _ticking_character()
    target.hp = 70
    status = ActiveStatus(name="regen", duration=2, value=8, source="isis")

    events: list[Event] = []
    ctx = StatusTickContext(
        status=status,
        character=target,
        player=None,  # type: ignore[arg-type]
        rng=SeededRandom(0),
        events=events,
    )
    RegenTick().tick(ctx)
    assert events[0].kind == "heal"
    assert events[0].details["source"] == "isis"
    assert events[0].details["tick"] == "regen"


def test_bleed_tick_falls_back_when_no_applier_known() -> None:
    target = _ticking_character()
    status = ActiveStatus(name="bleed", duration=2, value=5)  # no source

    events: list[Event] = []
    ctx = StatusTickContext(
        status=status,
        character=target,
        player=None,  # type: ignore[arg-type]
        rng=SeededRandom(0),
        events=events,
    )
    BleedTick().tick(ctx)
    # Fallback string for un-attributable statuses (e.g. arena-applied).
    assert events[0].details["source"] == "bleed"


# --------------------------------------------------------------------------- #
# summarize_events: healing + DoT attribution                                 #
# --------------------------------------------------------------------------- #


def test_summarize_attributes_healing() -> None:
    events = [
        Event(kind="heal", details={"source": "isis", "target": "athena", "value": 20}),
        Event(kind="heal", details={"source": "amaterasu", "target": "thor", "value": 12}),
        Event(kind="heal", details={"source": "regen", "target": "thor", "value": 5}),  # untracked
    ]
    summary = summarize_events(
        events,
        team_a=["isis", "athena", "anubis"],
        team_b=["amaterasu", "thor", "loki"],
        winner=None,
    )
    assert summary.healing_done_by_a == 20
    assert summary.healing_done_by_b == 12  # third event has unknown source


def test_summarize_attributes_dot_to_applier() -> None:
    """A poison tick with anubis as source counts as anubis's team's damage."""
    events = [
        Event(
            kind="damage",
            details={"source": "anubis", "tick": "poison", "target": "thor", "value": 10},
        ),
    ]
    summary = summarize_events(
        events,
        team_a=["achilles", "athena", "anubis"],
        team_b=["thor", "isis", "loki"],
        winner=None,
    )
    assert summary.damage_dealt_by_a == 10
    assert summary.damage_taken_by_b == 10


def test_summarize_skips_dot_with_environmental_source() -> None:
    """Arena-applied poison has source=`arena`, not a character — not credited."""
    events = [
        Event(
            kind="damage",
            details={"source": "arena", "tick": "poison", "target": "thor", "value": 5},
        ),
    ]
    summary = summarize_events(
        events,
        team_a=["achilles"],
        team_b=["thor"],
        winner=None,
    )
    assert summary.damage_dealt_by_a == 0
    assert summary.damage_dealt_by_b == 0
    # Target attribution still works.
    assert summary.damage_taken_by_b == 5
