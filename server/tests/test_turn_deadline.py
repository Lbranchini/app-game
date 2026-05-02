"""Server-side enforcement of the per-turn deadline.

Verifies the lifecycle wired into MatchRuntime:
  * `create_match_from_draft` seeds `state.turn_deadline`.
  * Each call to `submit_actions` re-arms the deadline.
  * `_auto_resolve_if_due` resolves an expired turn with empty actions.
  * The deadline check is race-safe: a real submission landing first
    causes the watcher to no-op.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import pytest

from agora.domain.draft import DraftPhase, DraftState
from agora.domain.enums import Side
from agora.infrastructure.yaml_arena_repository import YamlArenaRepository
from agora.infrastructure.yaml_repository import YamlCharacterRepository
from agora.interfaces.api.match_runtime import TURN_DURATION, MatchRuntime


@pytest.fixture
def runtime() -> MatchRuntime:
    return MatchRuntime(
        characters=YamlCharacterRepository(),
        arenas=YamlArenaRepository(),
    )


def _draft(side_a: str = "dev_a", side_b: str = "dev_b") -> DraftState:
    return DraftState(
        draft_id="d",
        arena_id="neutral",
        side_a_player_id=side_a,
        side_b_player_id=side_b,
        phase=DraftPhase.DONE,
        picks={
            Side.A: ["achilles", "athena", "anubis"],
            Side.B: ["thor", "isis", "loki"],
        },
    )


def test_initial_state_has_deadline(runtime: MatchRuntime) -> None:
    state = runtime.create_match_from_draft(_draft(), match_id="m", seed=1)
    assert state.turn_deadline is not None
    assert state.turn_deadline > datetime.utcnow()
    delta = state.turn_deadline - datetime.utcnow()
    assert delta <= TURN_DURATION
    assert delta > TURN_DURATION - timedelta(seconds=2)


def test_submit_re_arms_deadline(runtime: MatchRuntime) -> None:
    runtime.create_match_from_draft(_draft(), match_id="m", seed=1)
    first = runtime.get("m").turn_deadline
    assert first is not None

    new_state, _ = asyncio.run(runtime.submit_actions("m", []))
    second = new_state.turn_deadline
    assert second is not None
    assert second >= first


def test_auto_resolve_advances_turn_when_deadline_matches(runtime: MatchRuntime) -> None:
    runtime.create_match_from_draft(_draft(), match_id="m", seed=1)
    state = runtime.get("m")
    expected = state.turn_deadline
    assert expected is not None
    turn_before = state.turn

    asyncio.run(runtime._auto_resolve_if_due("m", expected))

    after = runtime.get("m")
    # Engine advances either turn count or current_side after resolve_turn.
    assert (after.turn != turn_before) or (after.current_side != state.current_side)
    assert after.turn_deadline is not None
    assert after.turn_deadline > expected


def test_auto_resolve_is_noop_when_deadline_shifted(runtime: MatchRuntime) -> None:
    runtime.create_match_from_draft(_draft(), match_id="m", seed=1)
    stale_deadline = datetime.utcnow() - timedelta(seconds=1)  # never matches

    snapshot = runtime.get("m").model_copy(deep=True)
    asyncio.run(runtime._auto_resolve_if_due("m", stale_deadline))
    after = runtime.get("m")
    assert after.turn == snapshot.turn
    assert after.current_side == snapshot.current_side


def test_finished_match_clears_deadline(runtime: MatchRuntime) -> None:
    runtime.create_match_from_draft(_draft(), match_id="m", seed=1)

    async def drive_to_finish() -> None:
        for _ in range(200):
            state = runtime.get("m")
            if state.finished:
                return
            # Wipe both teams to force a finished state on the next resolve.
            for ch in state.player(state.current_side).characters:
                ch.hp = 0
            for ch in state.opponent(state.current_side).characters:
                ch.hp = 0
            await runtime.submit_actions("m", [])

    asyncio.run(drive_to_finish())
    assert runtime.get("m").finished is True
    assert runtime.get("m").turn_deadline is None
