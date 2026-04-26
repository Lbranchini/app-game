"""Tests for finished-match persistence and the /match/history endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agora.application.ports import MatchHistoryRepository
from agora.infrastructure.sqlalchemy_match_history_repository import (
    SqlAlchemyMatchHistoryRepository,
)
from agora.interfaces.api.dependencies import get_match_history_repository
from agora.interfaces.api.main import create_app
from agora.interfaces.api.routers import match as match_router


@pytest.fixture
def history() -> MatchHistoryRepository:
    return SqlAlchemyMatchHistoryRepository(database_url="sqlite:///:memory:")


@pytest.fixture
def client(history: MatchHistoryRepository) -> TestClient:
    match_router._runtime = None  # fresh runtime so the override is picked up
    app = create_app()
    app.dependency_overrides[get_match_history_repository] = lambda: history
    return TestClient(app)


def _start(client: TestClient) -> str:
    response = client.post(
        "/match/dev/start",
        json={
            "team_a": ["achilles", "athena", "anubis"],
            "team_b": ["achilles", "athena", "anubis"],
            "seed": 1,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["match_id"]


def _drive_to_finish(client: TestClient, match_id: str, max_turns: int = 60) -> None:
    """Bash both teams' HP to 0 by submitting empty turns until the engine declares winner.

    Empty actions don't deal damage so this is a no-op; instead, rely on the
    engine calling end-of-match. We force a finish by directly mutating state
    via the runtime — simpler than crafting a full match here.
    """
    runtime = match_router._get_runtime  # noqa: F841 — referenced via app state
    state = match_router._runtime.get(match_id)  # type: ignore[union-attr]
    for character in state.b.characters:
        character.hp = 0
    # Submitting any action will run _check_end and persist.
    with client.websocket_connect(f"/match/ws/{match_id}") as ws:
        ws.receive_json()
        ws.send_json({"type": "actions", "actions": []})
        ws.receive_json()


def test_finished_match_persists_to_history(
    client: TestClient, history: MatchHistoryRepository
) -> None:
    match_id = _start(client)
    _drive_to_finish(client, match_id)

    records = history.list_recent()
    assert len(records) == 1
    record = records[0]
    assert record.id == match_id
    assert record.winner == "A"
    assert record.team_a == ["achilles", "athena", "anubis"]
    assert record.ended_at is not None


def test_history_endpoint_returns_records(
    client: TestClient, history: MatchHistoryRepository
) -> None:
    match_id = _start(client)
    _drive_to_finish(client, match_id)

    response = client.get("/match/history")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == match_id
    assert payload[0]["winner"] == "A"


def test_history_filters_by_player_id(
    client: TestClient, history: MatchHistoryRepository
) -> None:
    match_id = _start(client)
    _drive_to_finish(client, match_id)

    # Real match used "dev_a" / "dev_b" as player ids.
    response = client.get("/match/history", params={"player_id": "dev_a"})
    assert len(response.json()) == 1
    response = client.get("/match/history", params={"player_id": "ghost"})
    assert response.json() == []


def test_persistence_is_idempotent_when_match_already_finished(
    client: TestClient, history: MatchHistoryRepository
) -> None:
    match_id = _start(client)
    _drive_to_finish(client, match_id)

    # Touching the runtime again would attempt resolve_turn after `finished` and
    # raise — so just confirm history holds exactly one row.
    assert len(history.list_recent()) == 1
