"""Disconnect grace + forfeit lifecycle on MatchRuntime.

Each test exercises the runtime directly (no real WebSocket) — we attach
fake sockets that record `send_json` calls so the broadcast paths get
exercised.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import pytest

from agora.domain.draft import DraftPhase, DraftState
from agora.domain.enums import Side
from agora.infrastructure.yaml_arena_repository import YamlArenaRepository
from agora.infrastructure.yaml_repository import YamlCharacterRepository
from agora.interfaces.api.match_runtime import (
    DISCONNECT_GRACE,
    MatchRuntime,
)


class _FakeSocket:
    """Minimal stand-in for FastAPI's WebSocket — only what runtime touches."""

    def __init__(self) -> None:
        self.sent: list[dict[str, object]] = []
        self.closed = False

    async def send_json(self, payload: dict[str, object]) -> None:
        if self.closed:
            raise RuntimeError("socket closed")
        self.sent.append(payload)


@pytest.fixture
def runtime() -> MatchRuntime:
    return MatchRuntime(
        characters=YamlCharacterRepository(),
        arenas=YamlArenaRepository(),
    )


def _draft(side_a: str, side_b: str) -> DraftState:
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


def test_disconnect_starts_forfeit_clock_and_broadcasts(runtime: MatchRuntime) -> None:
    runtime.create_match_from_draft(_draft("alice", "bob"), match_id="m", seed=1)
    sock_a = _FakeSocket()
    sock_b = _FakeSocket()

    async def scenario() -> None:
        await runtime.attach("m", sock_a, player_id="alice")  # type: ignore[arg-type]
        await runtime.attach("m", sock_b, player_id="bob")  # type: ignore[arg-type]
        # Alice goes offline.
        await runtime.detach("m", sock_a)  # type: ignore[arg-type]

    asyncio.run(scenario())

    session = runtime._sessions["m"]
    assert "alice" in session.disconnected_since
    assert "alice" in session.forfeit_tasks
    # Bob got a presence frame announcing the forfeit clock.
    presence = [f for f in sock_b.sent if f.get("type") == "presence"]
    assert presence, "expected at least one presence frame"
    assert presence[-1]["status"] == "disconnected"
    assert presence[-1]["player_id"] == "alice"
    assert "forfeit_deadline" in presence[-1]


def test_reconnect_clears_disconnected_state(runtime: MatchRuntime) -> None:
    runtime.create_match_from_draft(_draft("alice", "bob"), match_id="m", seed=1)
    sock_a = _FakeSocket()
    sock_a2 = _FakeSocket()
    sock_b = _FakeSocket()

    async def scenario() -> None:
        await runtime.attach("m", sock_a, player_id="alice")  # type: ignore[arg-type]
        await runtime.attach("m", sock_b, player_id="bob")  # type: ignore[arg-type]
        await runtime.detach("m", sock_a)  # type: ignore[arg-type]
        await runtime.attach("m", sock_a2, player_id="alice")  # type: ignore[arg-type]

    asyncio.run(scenario())

    session = runtime._sessions["m"]
    assert "alice" not in session.disconnected_since
    # Forfeit task got cancelled.
    task = session.forfeit_tasks.get("alice")
    assert task is None or task.cancelled() or task.done()
    # Bob saw both transitions.
    presence = [f for f in sock_b.sent if f.get("type") == "presence"]
    assert any(f["status"] == "disconnected" for f in presence)
    assert any(f["status"] == "reconnected" for f in presence)


def test_forfeit_resolves_with_opposite_side_winner(runtime: MatchRuntime) -> None:
    runtime.create_match_from_draft(_draft("alice", "bob"), match_id="m", seed=1)
    sock_a = _FakeSocket()
    sock_b = _FakeSocket()

    async def scenario() -> None:
        await runtime.attach("m", sock_a, player_id="alice")  # type: ignore[arg-type]
        await runtime.attach("m", sock_b, player_id="bob")  # type: ignore[arg-type]
        await runtime.detach("m", sock_a)  # type: ignore[arg-type]
        # Force the forfeit to fire now by passing a deadline already in
        # the past — simulates "grace expired" without actually sleeping.
        since = runtime._sessions["m"].disconnected_since["alice"]
        await runtime._forfeit_if_still_disconnected("m", "alice", since)

    asyncio.run(scenario())

    state = runtime.get("m")
    assert state.finished is True
    assert state.winner == Side.B  # alice was on side A
    assert state.turn_deadline is None
    # Forfeit event broadcast to bob's socket.
    forfeits = [f for f in sock_b.sent if f.get("type") == "state"]
    assert any(
        any(e.get("kind") == "forfeit" for e in f.get("events", []))
        for f in forfeits
    )


def test_forfeit_noops_after_reconnect(runtime: MatchRuntime) -> None:
    """If the player came back before the grace expired, forfeit must not fire."""
    runtime.create_match_from_draft(_draft("alice", "bob"), match_id="m", seed=1)
    sock_a = _FakeSocket()

    async def scenario() -> None:
        await runtime.attach("m", sock_a, player_id="alice")  # type: ignore[arg-type]
        await runtime.detach("m", sock_a)  # type: ignore[arg-type]
        original_since = runtime._sessions["m"].disconnected_since["alice"]
        # Reconnect.
        await runtime.attach("m", sock_a, player_id="alice")  # type: ignore[arg-type]
        # Stale watcher fires with the original "disconnected since" timestamp.
        await runtime._forfeit_if_still_disconnected("m", "alice", original_since)

    asyncio.run(scenario())

    state = runtime.get("m")
    assert state.finished is False


def test_dev_match_does_not_track_disconnects(runtime: MatchRuntime) -> None:
    runtime.create_match_from_draft(_draft("dev_a", "dev_b"), match_id="m", seed=1)
    sock = _FakeSocket()

    async def scenario() -> None:
        # Real match flow only passes a player_id when there's a real user.
        await runtime.attach("m", sock, player_id=None)  # type: ignore[arg-type]
        await runtime.detach("m", sock)  # type: ignore[arg-type]

    asyncio.run(scenario())

    session = runtime._sessions["m"]
    assert session.disconnected_since == {}
    assert session.forfeit_tasks == {}


def test_grace_window_is_thirty_seconds() -> None:
    """A guardrail so we don't accidentally regress to a tighter window."""
    assert timedelta(seconds=30) == DISCONNECT_GRACE


def test_forfeit_skipped_when_match_already_finished(runtime: MatchRuntime) -> None:
    runtime.create_match_from_draft(_draft("alice", "bob"), match_id="m", seed=1)
    state = runtime.get("m")
    state.finished = True
    state.winner = Side.A

    async def scenario() -> None:
        await runtime._forfeit_if_still_disconnected("m", "alice", datetime.utcnow())

    asyncio.run(scenario())
    # Still A; forfeit logic must not flip the winner on a finished match.
    assert runtime.get("m").winner == Side.A
