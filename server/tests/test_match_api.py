"""Tests for the match REST + WebSocket endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agora.interfaces.api.main import create_app
from agora.interfaces.api.routers import match as match_router


@pytest.fixture(autouse=True)
def reset_runtime() -> None:
    """Each test starts with a fresh runtime so match ids don't leak."""
    match_router._runtime = None


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_dev_start_creates_match(client: TestClient) -> None:
    response = client.post(
        "/match/dev/start",
        json={
            "team_a": ["achilles", "athena", "anubis"],
            "team_b": ["thor", "isis", "loki"],
            "arena_id": "olympus",
            "seed": 7,
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["state"]["arena_id"] == "olympus"
    # Olympus +5 to Greek HP — Achilles base 110 → 115.
    assert payload["state"]["a"]["characters"][0]["hp_max"] == 115


def test_dev_start_rejects_wrong_team_size(client: TestClient) -> None:
    response = client.post(
        "/match/dev/start",
        json={
            "team_a": ["achilles", "athena"],
            "team_b": ["thor", "isis", "loki"],
        },
    )
    assert response.status_code == 400


def test_websocket_state_sync_after_action(client: TestClient) -> None:
    # 1. Create a match.
    started = client.post(
        "/match/dev/start",
        json={
            "team_a": ["achilles", "athena", "anubis"],
            "team_b": ["achilles", "athena", "anubis"],
            "seed": 1,
        },
    ).json()
    match_id = started["match_id"]

    # 2. Connect via WS, get the initial snapshot, submit a no-op turn.
    with client.websocket_connect(f"/match/ws/{match_id}") as ws:
        first = ws.receive_json()
        assert first["type"] == "state"
        assert first["state"]["match_id"] == match_id

        ws.send_json({"type": "actions", "actions": []})
        update = ws.receive_json()
        assert update["type"] == "state"
        # Turn advanced and side rotated.
        assert update["state"]["turn"] == 2
        assert update["state"]["current_side"] == "B"
        assert any(e["kind"] == "turn_started" for e in update["events"])


def test_websocket_unknown_frame_returns_error(client: TestClient) -> None:
    started = client.post(
        "/match/dev/start",
        json={
            "team_a": ["achilles", "athena", "anubis"],
            "team_b": ["achilles", "athena", "anubis"],
        },
    ).json()
    with client.websocket_connect(f"/match/ws/{started['match_id']}") as ws:
        ws.receive_json()  # initial snapshot
        ws.send_json({"type": "garbage"})
        error = ws.receive_json()
        assert error["type"] == "error"
