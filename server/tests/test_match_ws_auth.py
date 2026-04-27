"""Tests for the JWT + participant check on /match/ws/{id}."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agora.application.ports import PlayerRepository
from agora.domain.draft import DraftPhase, DraftState
from agora.domain.enums import Side
from agora.infrastructure.sqlalchemy_player_repository import SqlAlchemyPlayerRepository
from agora.interfaces.api.dependencies import get_player_repository
from agora.interfaces.api.main import create_app
from agora.interfaces.api.routers import match as match_router
from agora.interfaces.api.security import AuthenticatedUser, issue_access_token


@pytest.fixture
def players() -> PlayerRepository:
    return SqlAlchemyPlayerRepository(database_url="sqlite:///:memory:")


@pytest.fixture
def client(players: PlayerRepository) -> TestClient:
    match_router._runtime = None
    app = create_app()
    app.dependency_overrides[get_player_repository] = lambda: players
    return TestClient(app)


def _token(sub: str) -> str:
    return issue_access_token(AuthenticatedUser(sub=sub, email=None, name=None))


def _seed_match(client: TestClient, side_a_id: str, side_b_id: str, match_id: str = "m1") -> None:
    """Boot the runtime and stash a real-player match into it."""
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
        side_a_player_id=side_a_id,
        side_b_player_id=side_b_id,
        phase=DraftPhase.DONE,
        picks={Side.A: ["achilles", "athena", "anubis"], Side.B: ["thor", "isis", "loki"]},
    )
    rt.create_match_from_draft(draft, match_id=match_id, seed=1)


def test_real_match_requires_token(client: TestClient) -> None:
    _seed_match(client, "google:alice", "google:bob")
    with pytest.raises(Exception):
        with client.websocket_connect("/match/ws/m1"):
            pass


def test_real_match_rejects_non_participant(client: TestClient) -> None:
    _seed_match(client, "google:alice", "google:bob")
    eve = _token("google:eve")
    with pytest.raises(Exception):
        with client.websocket_connect(f"/match/ws/m1?token={eve}"):
            pass


def test_real_match_accepts_participant(client: TestClient) -> None:
    _seed_match(client, "google:alice", "google:bob")
    alice = _token("google:alice")
    with client.websocket_connect(f"/match/ws/m1?token={alice}") as ws:
        first = ws.receive_json()
        assert first["type"] == "state"


def test_dev_match_accepts_unauthenticated_socket(client: TestClient) -> None:
    """Dev matches (dev_a / dev_b) keep the existing un-auth flow."""
    started = client.post(
        "/match/dev/start",
        json={
            "team_a": ["achilles", "athena", "anubis"],
            "team_b": ["thor", "isis", "loki"],
        },
    ).json()
    with client.websocket_connect(f"/match/ws/{started['match_id']}") as ws:
        first = ws.receive_json()
        assert first["type"] == "state"
