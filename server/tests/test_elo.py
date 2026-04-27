"""Tests for ELO math, the player repo's update_elo path, and the
match-completion hook that updates ratings."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agora.application.ports import MatchHistoryRepository, PlayerRepository
from agora.domain.ratings import K_FACTOR, compute_new_ratings
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


# --------------------------------------------------------------------------- #
# Pure ELO formula                                                            #
# --------------------------------------------------------------------------- #


def test_equal_ratings_winner_takes_half_k() -> None:
    change = compute_new_ratings(1000, 1000, "A")
    assert change.delta_a == K_FACTOR // 2  # +16
    assert change.delta_b == -(K_FACTOR // 2)  # -16
    assert change.delta_a + change.delta_b == 0


def test_draw_at_equal_ratings_no_movement() -> None:
    change = compute_new_ratings(1000, 1000, None)
    assert change.delta_a == 0
    assert change.delta_b == 0


def test_underdog_win_gains_more() -> None:
    change = compute_new_ratings(rating_a=1200, rating_b=1500, winner="A")
    # The underdog (A) should pick up many more points than the favourite would.
    favourite = compute_new_ratings(rating_a=1500, rating_b=1200, winner="A")
    assert change.delta_a > favourite.delta_a
    # A always gains, B always loses, and totals remain symmetric.
    assert change.delta_a > 0
    assert change.delta_b < 0
    assert change.delta_a + change.delta_b == 0


def test_zero_sum() -> None:
    """Across all outcomes, A's gain equals B's loss to within rounding."""
    for winner in ("A", "B", None):
        change = compute_new_ratings(1234, 1456, winner)
        assert abs((change.delta_a + change.delta_b)) <= 1


# --------------------------------------------------------------------------- #
# Player repository: update_elo + get_by_provider                             #
# --------------------------------------------------------------------------- #


def _new_player_repo() -> SqlAlchemyPlayerRepository:
    return SqlAlchemyPlayerRepository(database_url="sqlite:///:memory:")


def test_update_elo_round_trips() -> None:
    repo = _new_player_repo()
    p = repo.upsert_by_provider(
        provider_subject="google:alice", email=None, name=None
    )
    assert p.elo == 1000
    updated = repo.update_elo(p.id, 1050)
    assert updated.elo == 1050
    refetched = repo.get_by_provider("google:alice")
    assert refetched is not None and refetched.elo == 1050


def test_get_by_provider_returns_none_for_unknown_subject() -> None:
    repo = _new_player_repo()
    assert repo.get_by_provider("google:nobody") is None


# --------------------------------------------------------------------------- #
# Integration — finished match updates both ELOs                              #
# --------------------------------------------------------------------------- #


@pytest.fixture
def players() -> PlayerRepository:
    return _new_player_repo()


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


def test_finished_match_updates_both_player_elos(
    client: TestClient,
    players: PlayerRepository,
) -> None:
    from agora.domain.draft import DraftPhase, DraftState
    from agora.domain.enums import Side
    from agora.interfaces.api.security import AuthenticatedUser, issue_access_token

    # Two real player rows.
    a = players.upsert_by_provider(provider_subject="google:alice", email=None, name="A")
    b = players.upsert_by_provider(provider_subject="google:bob", email=None, name="B")

    # Trigger runtime instantiation by hitting a REST endpoint that uses it.
    client.post(
        "/match/dev/start",
        json={
            "team_a": ["achilles", "athena", "anubis"],
            "team_b": ["thor", "isis", "loki"],
        },
    )
    rt = match_router._runtime
    assert rt is not None

    # Now build a match attributed to real subjects via the runtime directly.
    draft = DraftState(
        draft_id="test",
        arena_id="neutral",
        side_a_player_id="google:alice",
        side_b_player_id="google:bob",
        phase=DraftPhase.DONE,
        picks={Side.A: ["achilles", "athena", "anubis"], Side.B: ["thor", "isis", "loki"]},
    )
    state = rt.create_match_from_draft(draft, match_id="m1", seed=1)

    # Force a winner by zeroing side B's HP. Empty turn from A finishes the match.
    for character in state.b.characters:
        character.hp = 0

    alice_token = issue_access_token(
        AuthenticatedUser(sub="google:alice", email=None, name="A")
    )
    with client.websocket_connect(f"/match/ws/m1?token={alice_token}") as ws:
        ws.receive_json()
        ws.send_json({"type": "actions", "actions": []})
        ws.receive_json()

    new_a = players.get(a.id)
    new_b = players.get(b.id)
    assert new_a.elo > 1000  # winner gained
    assert new_b.elo < 1000  # loser lost
    assert (new_a.elo - 1000) + (new_b.elo - 1000) == 0  # zero-sum at equal ratings


def test_dev_match_does_not_touch_player_elos(
    client: TestClient, players: PlayerRepository
) -> None:
    """`/match/dev/start` uses dev_a/dev_b ids; no ELO update should happen."""
    # Pre-seed a real player with a non-default elo so we can detect change.
    p = players.upsert_by_provider(
        provider_subject="google:somebody", email=None, name=None
    )
    players.update_elo(p.id, 1234)

    started = client.post(
        "/match/dev/start",
        json={
            "team_a": ["achilles", "athena", "anubis"],
            "team_b": ["thor", "isis", "loki"],
            "seed": 1,
        },
    ).json()
    rt = match_router._runtime
    assert rt is not None
    state = rt.get(started["match_id"])
    for character in state.b.characters:
        character.hp = 0

    with client.websocket_connect(f"/match/ws/{started['match_id']}") as ws:
        ws.receive_json()
        ws.send_json({"type": "actions", "actions": []})
        ws.receive_json()

    assert players.get(p.id).elo == 1234  # untouched
