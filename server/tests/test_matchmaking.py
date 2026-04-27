"""Tests for the matchmaking queue and the draft WebSocket broadcast."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agora.application.use_cases.matchmaking import MatchmakingService, RandomArenaPicker
from agora.application.use_cases.draft import DraftService
from agora.domain.enums import Side
from agora.infrastructure.in_memory_draft_repository import InMemoryDraftRepository
from agora.infrastructure.yaml_arena_repository import YamlArenaRepository
from agora.interfaces.api.main import create_app
from agora.interfaces.api.routers import match as match_router
from agora.interfaces.api.security import AuthenticatedUser, issue_access_token


# --------------------------------------------------------------------------- #
# Service-level                                                               #
# --------------------------------------------------------------------------- #


def test_pairing_dequeues_two_players_and_creates_draft(
    repository: object,
) -> None:
    arenas = YamlArenaRepository()
    draft_service = DraftService(
        repository=InMemoryDraftRepository(),
        characters=repository,  # type: ignore[arg-type]
        arenas=arenas,
    )
    service = MatchmakingService(
        draft_service=draft_service,
        arena_picker=RandomArenaPicker(["neutral", "olympus"]),
    )

    assert service.try_pair() is None  # nobody queued yet

    service.join("google:alice", "Alice")
    assert service.try_pair() is None  # only one player

    service.join("google:bob", "Bob")
    pair = service.try_pair()
    assert pair is not None
    a, b, draft = pair
    assert a.player_id == "google:alice"
    assert b.player_id == "google:bob"
    assert draft.side_a_player_id == "google:alice"
    assert draft.side_b_player_id == "google:bob"
    assert draft.arena_id in {"neutral", "olympus"}
    # Queue is now empty.
    assert service.queued_player_ids() == []


def test_join_is_idempotent_per_player() -> None:
    arenas = YamlArenaRepository()
    draft_service = DraftService(
        repository=YamlArenaRepository(),  # type: ignore[arg-type]  # not actually used here
        characters=YamlArenaRepository(),  # type: ignore[arg-type]
        arenas=arenas,
    )
    service = MatchmakingService(
        draft_service=draft_service,
        arena_picker=RandomArenaPicker(["neutral"]),
    )
    service.join("google:alice")
    service.join("google:alice")
    service.join("google:alice")
    assert service.queued_player_ids() == ["google:alice"]


def test_leave_removes_from_queue() -> None:
    arenas = YamlArenaRepository()
    draft_service = DraftService(
        repository=YamlArenaRepository(),  # type: ignore[arg-type]
        characters=YamlArenaRepository(),  # type: ignore[arg-type]
        arenas=arenas,
    )
    service = MatchmakingService(
        draft_service=draft_service,
        arena_picker=RandomArenaPicker(["neutral"]),
    )
    service.join("google:alice")
    service.join("google:bob")
    service.leave("google:alice")
    assert service.queued_player_ids() == ["google:bob"]


# --------------------------------------------------------------------------- #
# WebSocket-level                                                             #
# --------------------------------------------------------------------------- #


@pytest.fixture(autouse=True)
def reset_runtime() -> None:
    match_router._runtime = None


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def _token(sub: str, name: str | None = None) -> str:
    return issue_access_token(AuthenticatedUser(sub=sub, email=None, name=name))


def test_two_players_queue_and_get_match_found_with_draft_id(client: TestClient) -> None:
    alice = _token("google:alice", "Alice")
    bob = _token("google:bob", "Bob")

    with client.websocket_connect(f"/matchmaking/ws?token={alice}") as ws_a:
        assert ws_a.receive_json() == {"type": "queued"}

        with client.websocket_connect(f"/matchmaking/ws?token={bob}") as ws_b:
            # Bob sees both his "queued" frame and the pairing notification.
            queued = ws_b.receive_json()
            match_found_b = ws_b.receive_json()
            match_found_a = ws_a.receive_json()

        assert queued == {"type": "queued"}
        assert match_found_a["type"] == "match_found"
        assert match_found_b["type"] == "match_found"
        assert match_found_a["draft_id"] == match_found_b["draft_id"]
        assert {match_found_a["side"], match_found_b["side"]} == {"A", "B"}


def test_matchmaking_ws_rejects_missing_token(client: TestClient) -> None:
    with pytest.raises(Exception):
        with client.websocket_connect("/matchmaking/ws"):
            pass  # close code 4401 — TestClient raises on rejection


def test_draft_ws_pushes_state_on_pick(client: TestClient) -> None:
    alice = _token("google:alice", "Alice")
    bob = _token("google:bob", "Bob")

    # Pair them first.
    with client.websocket_connect(f"/matchmaking/ws?token={alice}") as ws_a:
        ws_a.receive_json()  # queued
        with client.websocket_connect(f"/matchmaking/ws?token={bob}") as ws_b:
            ws_b.receive_json()  # queued
            ws_b.receive_json()  # match_found
            paired_a = ws_a.receive_json()
            draft_id = paired_a["draft_id"]

    # Now Alice subscribes to the draft WS and Bob mutates via REST; Alice should see it.
    with client.websocket_connect(f"/draft/ws/{draft_id}?token={alice}") as alice_ws:
        first = alice_ws.receive_json()
        assert first["type"] == "state"
        assert first["draft"]["draft_id"] == draft_id

        ban_response = client.post(
            f"/draft/{draft_id}/ban",
            json={"side": "A", "character_id": "loki"},
        )
        assert ban_response.status_code == 200

        update = alice_ws.receive_json()
        assert update["type"] == "state"
        assert update["draft"]["bans"]["A"] == "loki"


def test_draft_ws_rejects_non_participant(client: TestClient) -> None:
    """A token whose `sub` doesn't match either side gets a close, not a stream."""
    alice = _token("google:alice", "Alice")
    bob = _token("google:bob", "Bob")
    eve = _token("google:eve", "Eve")

    with client.websocket_connect(f"/matchmaking/ws?token={alice}") as ws_a:
        ws_a.receive_json()
        with client.websocket_connect(f"/matchmaking/ws?token={bob}") as ws_b:
            ws_b.receive_json()
            ws_b.receive_json()
            paired_a = ws_a.receive_json()
            draft_id = paired_a["draft_id"]

    with pytest.raises(Exception):
        with client.websocket_connect(f"/draft/ws/{draft_id}?token={eve}"):
            pass
