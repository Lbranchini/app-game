"""Regression: each player can only submit on their own side's turn.

Before this guard, both players could send `actions` frames at any time
and the engine would happily resolve them as the *current* side's turn —
so user-B could play user-A's characters whenever they queued first. The
WS handler now binds each socket to the side its JWT subject controls
and rejects out-of-turn submissions with a structured error.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agora.application.ports import PlayerRepository
from agora.domain.draft import DraftPhase, DraftState
from agora.domain.enums import Essence, Side
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


def _seed_match(client: TestClient) -> None:
    """Boot the runtime with a real-player match. Both sides start with
    enough vigor for one basic spear."""
    client.post(
        "/match/dev/start",
        json={
            "team_a": ["achilles", "athena", "anubis"],
            "team_b": ["achilles", "athena", "anubis"],
        },
    )
    rt = match_router._runtime
    assert rt is not None
    rt.create_match_from_draft(
        DraftState(
            draft_id="d",
            arena_id="neutral",
            side_a_player_id="google:alice",
            side_b_player_id="google:bob",
            phase=DraftPhase.DONE,
            picks={
                Side.A: ["achilles", "athena", "anubis"],
                Side.B: ["achilles", "athena", "anubis"],
            },
        ),
        match_id="m1",
        seed=1,
    )
    rt.get("m1").a.essences[Essence.VIGOR] = 1
    rt.get("m1").b.essences[Essence.VIGOR] = 1


def test_initial_state_frame_carries_your_side(client: TestClient) -> None:
    _seed_match(client)
    alice_token = issue_access_token(AuthenticatedUser(sub="google:alice", email=None, name=None))
    bob_token = issue_access_token(AuthenticatedUser(sub="google:bob", email=None, name=None))

    with client.websocket_connect(f"/match/ws/m1?token={alice_token}") as alice:
        alice_hello = alice.receive_json()
    with client.websocket_connect(f"/match/ws/m1?token={bob_token}") as bob:
        bob_hello = bob.receive_json()

    assert alice_hello["type"] == "state"
    assert alice_hello["your_side"] == "A"
    assert bob_hello["type"] == "state"
    assert bob_hello["your_side"] == "B"


def test_off_turn_submission_is_rejected(client: TestClient) -> None:
    """Bob submits during Alice's (side A's) turn — must be rejected, no
    state change for either side."""
    _seed_match(client)
    alice_token = issue_access_token(AuthenticatedUser(sub="google:alice", email=None, name=None))
    bob_token = issue_access_token(AuthenticatedUser(sub="google:bob", email=None, name=None))

    rt = match_router._runtime
    assert rt is not None
    turns_before = rt.get("m1").turn

    with (
        client.websocket_connect(f"/match/ws/m1?token={alice_token}") as alice,
        client.websocket_connect(f"/match/ws/m1?token={bob_token}") as bob,
    ):
        alice.receive_json()
        bob.receive_json()
        # It's A's turn. Bob tries to submit anyway.
        bob.send_json(
            {
                "type": "actions",
                "actions": [
                    {
                        "character_id": "achilles",
                        "skill_id": "spear",
                        "target_ids": ["achilles"],
                        "paid": {"vigor": 1},
                    }
                ],
            }
        )
        err = bob.receive_json()
        assert err["type"] == "error"
        # Stable machine code so the client can localize via i18n; English
        # detail kept as the fallback for older clients.
        assert err["code"] == "match.not_your_turn"
        assert "not your turn" in err["detail"]

    # No turn was resolved — counters and state untouched.
    assert rt.get("m1").turn == turns_before
    assert rt.get("m1").a.characters[0].hp == rt.get("m1").a.characters[0].hp_max


def test_unknown_frame_returns_stable_error_code(client: TestClient) -> None:
    """Any non-`actions` frame should round-trip with the documented code."""
    _seed_match(client)
    alice_token = issue_access_token(AuthenticatedUser(sub="google:alice", email=None, name=None))

    with client.websocket_connect(f"/match/ws/m1?token={alice_token}") as alice:
        alice.receive_json()
        alice.send_json({"type": "ping"})
        err = alice.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "match.unknown_frame"


def test_alternating_submissions_resolve_normally(client: TestClient) -> None:
    """Sanity check: when each player submits on their own turn the engine
    keeps resolving as before."""
    _seed_match(client)
    alice_token = issue_access_token(AuthenticatedUser(sub="google:alice", email=None, name=None))
    bob_token = issue_access_token(AuthenticatedUser(sub="google:bob", email=None, name=None))

    rt = match_router._runtime
    assert rt is not None

    with (
        client.websocket_connect(f"/match/ws/m1?token={alice_token}") as alice,
        client.websocket_connect(f"/match/ws/m1?token={bob_token}") as bob,
    ):
        alice.receive_json()
        bob.receive_json()
        # A's turn — Alice submits.
        alice.send_json({"type": "actions", "actions": []})
        alice.receive_json()
        bob.receive_json()
        assert rt.get("m1").current_side is Side.B

        # B's turn — Bob submits.
        bob.send_json({"type": "actions", "actions": []})
        bob.receive_json()
        alice.receive_json()
        assert rt.get("m1").current_side is Side.A
        assert rt.get("m1").turn >= 3


def test_dev_match_keeps_hot_seat_behaviour(client: TestClient) -> None:
    """Dev matches don't have real player ids; either submission is allowed
    so the local hot-seat demo flow still works."""
    resp = client.post(
        "/match/dev/start",
        json={
            "team_a": ["achilles", "athena", "anubis"],
            "team_b": ["thor", "isis", "loki"],
        },
    )
    match_id = resp.json()["match_id"]
    with client.websocket_connect(f"/match/ws/{match_id}") as ws:
        first = ws.receive_json()
        assert first["type"] == "state"
        assert first["your_side"] is None
        ws.send_json({"type": "actions", "actions": []})
        update = ws.receive_json()
        assert update["type"] == "state"
