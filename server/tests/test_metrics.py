"""Prometheus scrape contract.

We test the surface clients see (a 200 with text-format payload that
mentions every metric we promise) plus the bumps the runtime drives.
The Prometheus client deduplicates registrations across `create_app()`
calls, so each test runs against a fresh `TestClient` to keep the
numbers isolated.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agora.application.ports import PlayerRepository
from agora.domain.draft import DraftPhase, DraftState
from agora.domain.enums import Side
from agora.infrastructure.sqlalchemy_player_repository import SqlAlchemyPlayerRepository
from agora.interfaces.api import metrics as metrics_module
from agora.interfaces.api.dependencies import get_player_repository
from agora.interfaces.api.main import create_app
from agora.interfaces.api.routers import match as match_router


@pytest.fixture
def players() -> PlayerRepository:
    return SqlAlchemyPlayerRepository(database_url="sqlite:///:memory:")


@pytest.fixture
def client(players: PlayerRepository) -> TestClient:
    # Reset gauges so the per-test snapshot is deterministic.
    metrics_module.active_matches.set(0)
    metrics_module.matchmaking_queue_depth.set(0)
    match_router._runtime = None
    app = create_app()
    app.dependency_overrides[get_player_repository] = lambda: players
    return TestClient(app)


def test_metrics_endpoint_returns_prometheus_text(client: TestClient) -> None:
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    body = resp.text
    # Every metric the module promises shows up at least as a HELP line.
    for metric_name in (
        "agora_active_matches",
        "agora_matches_finished_total",
        "agora_matches_forfeited_total",
        "agora_turn_resolve_seconds",
        "agora_matchmaking_queue_depth",
    ):
        assert metric_name in body, f"missing {metric_name} in /metrics output"


def test_active_matches_gauge_bumps_on_dev_start(client: TestClient) -> None:
    body = {
        "team_a": ["achilles", "athena", "anubis"],
        "team_b": ["thor", "isis", "loki"],
        "arena_id": "neutral",
        "seed": 1,
    }
    assert client.post("/match/dev/start", json=body).status_code == 200
    assert client.post("/match/dev/start", json=body).status_code == 200

    body = client.get("/metrics").text
    # Two active matches now, 0 finished. The Prometheus text format prints
    # gauges on a line that ends with the value.
    assert "agora_active_matches 2.0" in body


def test_matches_finished_counter_bumps_on_dev_match_end(client: TestClient) -> None:
    body = {
        "team_a": ["achilles", "athena", "anubis"],
        "team_b": ["thor", "isis", "loki"],
        "arena_id": "neutral",
        "seed": 1,
    }
    started = client.post("/match/dev/start", json=body).json()
    rt = match_router._runtime
    assert rt is not None
    # Force the match into a finished-by-A state and run the persist hook.
    session = rt._sessions[started["match_id"]]
    session.state.finished = True
    session.state.winner = Side.A
    rt._maybe_persist(started["match_id"], session)

    body = client.get("/metrics").text
    assert 'agora_matches_finished_total{winner="A"} 1.0' in body
    # Gauge dropped back to zero now that the match is over.
    assert "agora_active_matches 0.0" in body


def _draft_for(side_a: str, side_b: str) -> DraftState:
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


def test_matches_forfeited_counter_bumps_on_grace_expiry(
    client: TestClient,
) -> None:
    """A real-player match driven through `_forfeit_if_still_disconnected`
    should bump the forfeit counter, not just the regular finished counter."""
    import asyncio
    from datetime import datetime

    # Boot the runtime with a real-player draft.
    client.post(
        "/match/dev/start",
        json={
            "team_a": ["achilles", "athena", "anubis"],
            "team_b": ["thor", "isis", "loki"],
        },
    )
    rt = match_router._runtime
    assert rt is not None
    rt.create_match_from_draft(_draft_for("alice", "bob"), match_id="m1", seed=1)

    async def scenario() -> None:
        # Skip the actual socket dance — we're isolating the forfeit handler.
        rt._sessions["m1"].disconnected_since["alice"] = datetime.utcnow()
        await rt._forfeit_if_still_disconnected(
            "m1", "alice", rt._sessions["m1"].disconnected_since["alice"]
        )

    asyncio.run(scenario())

    body = client.get("/metrics").text
    assert "agora_matches_forfeited_total 1.0" in body
    assert 'agora_matches_finished_total{winner="B"} 1.0' in body  # Alice was A
