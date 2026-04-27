"""Tests for the enriched /auth/me payload and the post-match win/loss counters."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agora.application.ports import MatchHistoryRepository, PlayerRepository
from agora.application.use_cases.missions import MissionService
from agora.domain.draft import DraftPhase, DraftState
from agora.domain.enums import Side
from agora.infrastructure.sqlalchemy_match_history_repository import (
    SqlAlchemyMatchHistoryRepository,
)
from agora.infrastructure.sqlalchemy_player_repository import SqlAlchemyPlayerRepository
from agora.interfaces.api.dependencies import (
    get_match_history_repository,
    get_player_repository,
)
from agora.interfaces.api.main import create_app
from agora.interfaces.api.routers import match as match_router
from agora.interfaces.api.security import AuthenticatedUser, issue_access_token


@pytest.fixture
def players() -> PlayerRepository:
    return SqlAlchemyPlayerRepository(database_url="sqlite:///:memory:")


@pytest.fixture
def history() -> MatchHistoryRepository:
    return SqlAlchemyMatchHistoryRepository(database_url="sqlite:///:memory:")


@pytest.fixture
def client(
    players: PlayerRepository, history: MatchHistoryRepository
) -> TestClient:
    match_router._runtime = None
    app = create_app()
    app.dependency_overrides[get_player_repository] = lambda: players
    app.dependency_overrides[get_match_history_repository] = lambda: history
    return TestClient(app)


def _token(sub: str, name: str | None = None) -> str:
    return issue_access_token(AuthenticatedUser(sub=sub, email=None, name=name))


# --------------------------------------------------------------------------- #
# /auth/me                                                                    #
# --------------------------------------------------------------------------- #


def test_me_returns_null_player_when_row_missing(client: TestClient) -> None:
    response = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {_token('google:nobody')}"}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["sub"] == "google:nobody"
    assert payload["player"] is None


def test_me_includes_persisted_player_with_elo_and_roster(
    client: TestClient, players: PlayerRepository
) -> None:
    p = players.upsert_by_provider(
        provider_subject="google:alice", email="a@b.com", name="Alice"
    )
    players.update_elo(p.id, 1175)

    response = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {_token('google:alice', 'Alice')}"}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["player"]["id"] == p.id
    assert payload["player"]["elo"] == 1175
    assert "achilles" in payload["player"]["unlocked_characters"]


# --------------------------------------------------------------------------- #
# MissionService — service-level                                              #
# --------------------------------------------------------------------------- #


def test_mission_service_increments_winner_and_loser(
    players: PlayerRepository,
) -> None:
    a = players.upsert_by_provider(provider_subject="google:alice", email=None, name=None)
    b = players.upsert_by_provider(provider_subject="google:bob", email=None, name=None)
    service = MissionService(players)

    service.record_match_outcome(
        side_a_subject="google:alice",
        side_b_subject="google:bob",
        winner="A",
    )

    after_a = players.get(a.id)
    after_b = players.get(b.id)
    assert after_a.progress["wins"] == 1
    assert after_a.progress["matches_played"] == 1
    assert after_b.progress["losses"] == 1
    assert after_b.progress["matches_played"] == 1


def test_mission_service_records_draws(players: PlayerRepository) -> None:
    a = players.upsert_by_provider(provider_subject="google:alice", email=None, name=None)
    b = players.upsert_by_provider(provider_subject="google:bob", email=None, name=None)
    service = MissionService(players)

    service.record_match_outcome(
        side_a_subject="google:alice",
        side_b_subject="google:bob",
        winner=None,
    )
    assert players.get(a.id).progress.get("draws", 0) == 1
    assert players.get(b.id).progress.get("draws", 0) == 1


def test_mission_service_skips_unknown_subjects(players: PlayerRepository) -> None:
    """Dev / synthetic subjects don't have a row; the service silently skips them."""
    service = MissionService(players)
    # Should not raise.
    service.record_match_outcome(
        side_a_subject="dev_a",
        side_b_subject="dev_b",
        winner="A",
    )


# --------------------------------------------------------------------------- #
# Integration — finished match increments both players' counters              #
# --------------------------------------------------------------------------- #


def test_finished_match_increments_progress_counters(
    client: TestClient, players: PlayerRepository
) -> None:
    a = players.upsert_by_provider(provider_subject="google:alice", email=None, name=None)
    b = players.upsert_by_provider(provider_subject="google:bob", email=None, name=None)

    # Boot the runtime and stash a real-player match into it.
    client.post(
        "/match/dev/start",
        json={
            "team_a": ["achilles", "athena", "anubis"],
            "team_b": ["thor", "isis", "loki"],
        },
    )
    rt = match_router._runtime
    assert rt is not None
    draft = DraftState(
        draft_id="d",
        arena_id="neutral",
        side_a_player_id="google:alice",
        side_b_player_id="google:bob",
        phase=DraftPhase.DONE,
        picks={Side.A: ["achilles", "athena", "anubis"], Side.B: ["thor", "isis", "loki"]},
    )
    state = rt.create_match_from_draft(draft, match_id="mp", seed=1)
    for character in state.b.characters:
        character.hp = 0  # force A win

    alice_token = _token("google:alice")
    with client.websocket_connect(f"/match/ws/mp?token={alice_token}") as ws:
        ws.receive_json()
        ws.send_json({"type": "actions", "actions": []})
        ws.receive_json()

    after_a = players.get(a.id)
    after_b = players.get(b.id)
    assert after_a.progress["wins"] == 1
    assert after_b.progress["losses"] == 1
