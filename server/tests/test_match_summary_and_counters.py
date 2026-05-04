"""Tests for the match telemetry pipeline:

  events  →  summarize_events  →  MatchSummary
                       ↓
              MissionService writes richer counters
                       ↓
              UnlockService picks up new thresholds
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agora.application.ports import MatchHistoryRepository, PlayerRepository
from agora.application.use_cases.match_summary import summarize_events
from agora.application.use_cases.missions import MissionService
from agora.domain.draft import DraftPhase, DraftState
from agora.domain.enums import Essence, Side
from agora.domain.events import Event
from agora.domain.match import Action
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
# summarize_events — pure                                                     #
# --------------------------------------------------------------------------- #


def test_summarize_attributes_damage_to_correct_team() -> None:
    events = [
        Event(kind="damage", details={"source": "achilles", "target": "thor", "value": 20}),
        Event(kind="damage", details={"source": "thor", "target": "achilles", "value": 25}),
        Event(kind="damage", details={"source": "poison", "target": "achilles", "value": 10}),
    ]
    summary = summarize_events(
        events,
        team_a=["achilles", "athena", "anubis"],
        team_b=["thor", "isis", "loki"],
        winner="A",
    )
    assert summary.damage_dealt_by_a == 20  # Achilles' spear
    assert summary.damage_dealt_by_b == 25  # Thor's mjolnir
    # Achilles took poison + Thor's hit; Thor took Achilles' hit.
    assert summary.damage_taken_by_a == 25 + 10
    assert summary.damage_taken_by_b == 20


def test_summarize_attributes_status_applied_by_source_team() -> None:
    events = [
        Event(
            kind="status_applied",
            details={
                "character": "thor",
                "status": "poison",
                "duration": 2,
                "value": 10,
                "source": "anubis",
            },
        ),
        Event(
            kind="status_applied",
            details={
                "character": "achilles",
                "status": "stun",
                "duration": 1,
                "value": 0,
                "source": "loki",
            },
        ),
    ]
    summary = summarize_events(
        events,
        team_a=["achilles", "athena", "anubis"],
        team_b=["thor", "isis", "loki"],
        winner=None,
    )
    assert summary.status_applied_by_a == {"poison": 1}
    assert summary.status_applied_by_b == {"stun": 1}


def test_summarize_ignores_events_with_unknown_actor() -> None:
    events = [
        Event(kind="damage", details={"source": "godzilla", "target": "thor", "value": 99}),
        Event(kind="status_applied", details={"character": "x", "status": "y", "source": "ghost"}),
    ]
    summary = summarize_events(events, team_a=["a"], team_b=["b"], winner=None)
    assert summary.damage_dealt_by_a == 0
    assert summary.damage_dealt_by_b == 0
    assert summary.status_applied_by_a == {}


# --------------------------------------------------------------------------- #
# MissionService writes richer counters                                       #
# --------------------------------------------------------------------------- #


def _new_player_repo() -> SqlAlchemyPlayerRepository:
    return SqlAlchemyPlayerRepository(database_url="sqlite:///:memory:")


def test_mission_service_records_telemetry() -> None:
    repo = _new_player_repo()
    a = repo.upsert_by_provider(provider_subject="google:alice", email=None, name=None)
    b = repo.upsert_by_provider(provider_subject="google:bob", email=None, name=None)

    summary = summarize_events(
        [
            Event(kind="damage", details={"source": "achilles", "target": "thor", "value": 30}),
            Event(
                kind="status_applied",
                details={
                    "character": "thor",
                    "status": "silence",
                    "duration": 2,
                    "value": 0,
                    "source": "athena",
                },
            ),
        ],
        team_a=["achilles", "athena", "anubis"],
        team_b=["thor", "isis", "loki"],
        winner="A",
    )

    service = MissionService(repo)
    service.record_match_outcome(
        side_a_subject="google:alice",
        side_b_subject="google:bob",
        winner="A",
        summary=summary,
    )

    after_a = repo.get(a.id)
    after_b = repo.get(b.id)
    assert after_a.progress["wins"] == 1
    assert after_a.progress["total_damage_dealt"] == 30
    assert after_a.progress["status_applied.silence"] == 1
    assert after_b.progress["losses"] == 1
    assert after_b.progress["total_damage_taken"] == 30


# --------------------------------------------------------------------------- #
# Integration: a full match accumulates real telemetry counters               #
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


def test_real_match_records_damage_and_status_counters(
    client: TestClient, players: PlayerRepository
) -> None:
    """Run a real match where Anubis applies poison so the counters move."""
    a = players.upsert_by_provider(provider_subject="google:alice", email=None, name=None)
    players.upsert_by_provider(provider_subject="google:bob", email=None, name=None)

    # Boot the runtime.
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
        picks={
            Side.A: ["achilles", "athena", "anubis"],
            Side.B: ["achilles", "athena", "anubis"],
        },
    )
    state = rt.create_match_from_draft(draft, match_id="mt", seed=1)

    # Pre-load Anubis with the Blood essence the wraps skill needs.
    rt.get("mt").a.essences[Essence.BLOOD] = 1

    alice_token = issue_access_token(
        AuthenticatedUser(sub="google:alice", email=None, name=None)
    )
    bob_token = issue_access_token(
        AuthenticatedUser(sub="google:bob", email=None, name=None)
    )
    with (
        client.websocket_connect(f"/match/ws/mt?token={alice_token}") as alice_ws,
        client.websocket_connect(f"/match/ws/mt?token={bob_token}") as bob_ws,
    ):
        alice_ws.receive_json()
        bob_ws.receive_json()
        # Anubis (side A) casts Choking Wraps on B's Achilles — 10 damage + poison.
        action = Action(
            character_id="anubis",
            skill_id="wraps",
            target_ids=["achilles"],
            paid={Essence.BLOOD: 1},
        )
        alice_ws.send_json({"type": "actions", "actions": [action.model_dump()]})
        alice_ws.receive_json()
        bob_ws.receive_json()

        # Force B's HP to 0 on the *current* session state — `rt.get` returns
        # the live reference, which the engine deep-copied after the previous
        # turn. Bob (now the active side) submits an empty turn so the engine
        # flips the match to finished and the counters fire.
        for character in rt.get("mt").b.characters:
            character.hp = 0
        bob_ws.send_json({"type": "actions", "actions": []})
        bob_ws.receive_json()
        alice_ws.receive_json()

    after_a = players.get(a.id)
    assert after_a.progress["total_damage_dealt"] >= 10
    # Anubis applied poison once at minimum.
    assert after_a.progress.get("status_applied.poison", 0) >= 1
