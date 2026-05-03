"""Server-side application heartbeat — detect silently-dead sockets faster
than the OS-level TCP timeout (which on Linux defaults to ~2 hours).

We don't drive the asyncio loop in real time here; instead we exercise the
heartbeat loop's body directly by patching the interval to a tiny value.
"""

from __future__ import annotations

import asyncio

import pytest

from agora.domain.draft import DraftPhase, DraftState
from agora.domain.enums import Side
from agora.infrastructure.yaml_arena_repository import YamlArenaRepository
from agora.infrastructure.yaml_repository import YamlCharacterRepository
from agora.interfaces.api import match_runtime
from agora.interfaces.api.match_runtime import MatchRuntime


class _FakeSocket:
    """Records every send_json. Set `should_fail=True` to simulate a dead pipe."""

    def __init__(self, should_fail: bool = False) -> None:
        self.sent: list[dict[str, object]] = []
        self.should_fail = should_fail

    async def send_json(self, payload: dict[str, object]) -> None:
        if self.should_fail:
            raise ConnectionError("pipe broken")
        self.sent.append(payload)


@pytest.fixture
def runtime() -> MatchRuntime:
    return MatchRuntime(
        characters=YamlCharacterRepository(),
        arenas=YamlArenaRepository(),
    )


def _draft(side_a: str = "alice", side_b: str = "bob") -> DraftState:
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


def test_heartbeat_loop_is_armed_on_first_attach(runtime: MatchRuntime) -> None:
    runtime.create_match_from_draft(_draft(), match_id="m", seed=1)
    sock = _FakeSocket()

    captured: dict[str, object] = {}

    async def scenario() -> None:
        await runtime.attach("m", sock, player_id="alice")  # type: ignore[arg-type]
        # Inspect the task while the loop is still alive — once asyncio.run
        # tears the loop down, all background tasks are cancelled.
        task = runtime._sessions["m"].heartbeat_task
        captured["exists"] = task is not None
        captured["live"] = task is not None and not task.done()
        if task:
            task.cancel()

    asyncio.run(scenario())

    assert captured["exists"] is True
    assert captured["live"] is True


def test_heartbeat_pushes_payload_to_each_attached_socket(
    runtime: MatchRuntime, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Patch the interval to ~0 so one tick lands quickly, then cancel."""
    monkeypatch.setattr(match_runtime, "HEARTBEAT_INTERVAL_SECONDS", 0.01)
    runtime.create_match_from_draft(_draft(), match_id="m", seed=1)
    sock_a = _FakeSocket()
    sock_b = _FakeSocket()

    async def scenario() -> None:
        await runtime.attach("m", sock_a, player_id="alice")  # type: ignore[arg-type]
        await runtime.attach("m", sock_b, player_id="bob")  # type: ignore[arg-type]
        # Give the heartbeat loop a couple of ticks to fire.
        await asyncio.sleep(0.05)
        # Stop the loop so the test exits cleanly.
        task = runtime._sessions["m"].heartbeat_task
        if task:
            task.cancel()

    asyncio.run(scenario())

    assert any(f.get("type") == "heartbeat" for f in sock_a.sent)
    assert any(f.get("type") == "heartbeat" for f in sock_b.sent)


def test_heartbeat_detaches_dead_sockets(
    runtime: MatchRuntime, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A socket whose send_json blows up should be detached automatically."""
    monkeypatch.setattr(match_runtime, "HEARTBEAT_INTERVAL_SECONDS", 0.01)
    runtime.create_match_from_draft(_draft(), match_id="m", seed=1)
    dead = _FakeSocket(should_fail=True)
    live = _FakeSocket()

    async def scenario() -> None:
        await runtime.attach("m", dead, player_id="alice")  # type: ignore[arg-type]
        await runtime.attach("m", live, player_id="bob")  # type: ignore[arg-type]
        await asyncio.sleep(0.05)
        task = runtime._sessions["m"].heartbeat_task
        if task:
            task.cancel()

    asyncio.run(scenario())

    session = runtime._sessions["m"]
    # Dead socket got detached; live one stayed.
    assert dead not in [s for _, s in session.sockets]
    assert live in [s for _, s in session.sockets]
    # Forfeit clock now ticking on the player whose socket died.
    assert "alice" in session.disconnected_since


def test_heartbeat_torn_down_when_match_finishes(
    runtime: MatchRuntime,
) -> None:
    runtime.create_match_from_draft(_draft(), match_id="m", seed=1)
    sock = _FakeSocket()

    async def scenario() -> None:
        await runtime.attach("m", sock, player_id="alice")  # type: ignore[arg-type]
        # Force the match into a finished state, then trigger persist
        # (which the runtime calls inside submit_actions/forfeit paths).
        session = runtime._sessions["m"]
        session.state.finished = True
        runtime._maybe_persist("m", session)
        # Heartbeat task should have been cancelled.
        task = session.heartbeat_task
        if task is not None:
            await asyncio.sleep(0)  # let the cancel propagate
            assert task.cancelled() or task.done()

    asyncio.run(scenario())
