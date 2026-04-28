"""Tests for unlock thresholds and ELO-delta persistence on match records."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agora.application.ports import MatchHistoryRepository, PlayerRepository
from agora.application.use_cases.unlocks import (
    DEFAULT_RULES,
    UnlockRule,
    UnlockService,
)
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


# --------------------------------------------------------------------------- #
# UnlockService — pure logic                                                  #
# --------------------------------------------------------------------------- #


def _new_player_repo() -> SqlAlchemyPlayerRepository:
    return SqlAlchemyPlayerRepository(database_url="sqlite:///:memory:")


def test_unlock_service_idempotent_when_thresholds_unmet() -> None:
    repo = _new_player_repo()
    p = repo.upsert_by_provider(provider_subject="google:alice", email=None, name=None)
    service = UnlockService(repo)
    assert service.apply(p.id) == []
    # No write happened — unlocked roster unchanged.
    assert set(repo.get(p.id).unlocked_characters) == set(p.unlocked_characters)


def test_unlock_service_unlocks_medusa_at_five_wins() -> None:
    repo = _new_player_repo()
    p = repo.upsert_by_provider(provider_subject="google:alice", email=None, name=None)
    repo.update_progress(p.id, {"wins": 5, "matches_played": 5})
    service = UnlockService(repo)
    assert service.apply(p.id) == ["medusa"]
    assert "medusa" in repo.get(p.id).unlocked_characters


def test_unlock_service_does_not_double_unlock() -> None:
    repo = _new_player_repo()
    p = repo.upsert_by_provider(provider_subject="google:alice", email=None, name=None)
    repo.update_progress(p.id, {"wins": 5, "matches_played": 5})
    service = UnlockService(repo)
    service.apply(p.id)
    # Calling again returns nothing newly unlocked.
    assert service.apply(p.id) == []


def test_unlock_service_evaluates_multiple_rules() -> None:
    repo = _new_player_repo()
    p = repo.upsert_by_provider(provider_subject="google:alice", email=None, name=None)
    repo.update_progress(p.id, {"wins": 10, "matches_played": 10})
    service = UnlockService(repo)
    # 10 wins triggers both medusa (>=5) and sun_wukong (>=10).
    newly = set(service.apply(p.id))
    assert newly == {"medusa", "sun_wukong"}


def test_default_rule_set_targets_documented_characters() -> None:
    # Sanity: every rule in the default registry references a character id
    # we ship in `data/characters/`. Catches drift if a rule is added
    # without its YAML.
    expected = {
        "medusa",
        "sun_wukong",
        "mulan",
        "amaterasu",
        "cleopatra",
        "inanna",
        "quetzalcoatl",
        "king_arthur",
    }
    assert {r.character_id for r in DEFAULT_RULES} == expected


def test_custom_rule_set_overrides_defaults() -> None:
    repo = _new_player_repo()
    p = repo.upsert_by_provider(provider_subject="google:alice", email=None, name=None)
    repo.update_progress(p.id, {"wins": 1})
    custom = (
        UnlockRule(
            character_id="anubis",  # already a starter — should be filtered out
            description="Test",
            predicate=lambda _player: True,
        ),
    )
    service = UnlockService(repo, rules=custom)
    # `anubis` is already in the starter pool, so apply() returns nothing new.
    assert service.apply(p.id) == []


# --------------------------------------------------------------------------- #
# Integration — MatchRecord persists ELO deltas                               #
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


def _drive_real_match_to_finish(
    client: TestClient,
    players: PlayerRepository,
    *,
    side_a: str = "google:alice",
    side_b: str = "google:bob",
    match_id: str = "m1",
) -> None:
    players.upsert_by_provider(provider_subject=side_a, email=None, name=None)
    players.upsert_by_provider(provider_subject=side_b, email=None, name=None)
    # Boot the runtime via a REST call.
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
        side_a_player_id=side_a,
        side_b_player_id=side_b,
        phase=DraftPhase.DONE,
        picks={Side.A: ["achilles", "athena", "anubis"], Side.B: ["thor", "isis", "loki"]},
    )
    state = rt.create_match_from_draft(draft, match_id=match_id, seed=1)
    for character in state.b.characters:
        character.hp = 0  # force A win
    token = issue_access_token(AuthenticatedUser(sub=side_a, email=None, name=None))
    with client.websocket_connect(f"/match/ws/{match_id}?token={token}") as ws:
        ws.receive_json()
        ws.send_json({"type": "actions", "actions": []})
        ws.receive_json()


def test_finished_real_match_persists_elo_deltas(
    client: TestClient,
    players: PlayerRepository,
    history: MatchHistoryRepository,
) -> None:
    _drive_real_match_to_finish(client, players)
    records = history.list_recent()
    assert len(records) == 1
    record = records[0]
    assert record.elo_delta_a is not None and record.elo_delta_a > 0
    assert record.elo_delta_b is not None and record.elo_delta_b < 0
    assert record.elo_delta_a + record.elo_delta_b == 0


def test_dev_match_persists_null_deltas(
    client: TestClient, history: MatchHistoryRepository
) -> None:
    started = client.post(
        "/match/dev/start",
        json={
            "team_a": ["achilles", "athena", "anubis"],
            "team_b": ["thor", "isis", "loki"],
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

    records = history.list_recent()
    assert len(records) == 1
    assert records[0].elo_delta_a is None
    assert records[0].elo_delta_b is None


def test_winning_five_real_matches_unlocks_medusa(
    client: TestClient, players: PlayerRepository
) -> None:
    for i in range(5):
        _drive_real_match_to_finish(client, players, match_id=f"m{i}")

    alice = players.get_by_provider("google:alice")
    assert alice is not None
    assert "medusa" in alice.unlocked_characters
