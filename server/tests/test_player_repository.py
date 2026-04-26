"""Tests for the SQLAlchemy player repository (against in-memory SQLite)."""

from __future__ import annotations

from datetime import datetime

from agora.domain.player import DEFAULT_STARTERS
from agora.infrastructure.sqlalchemy_player_repository import SqlAlchemyPlayerRepository


def _new_repo() -> SqlAlchemyPlayerRepository:
    # Each test gets a fresh in-memory database.
    return SqlAlchemyPlayerRepository(database_url="sqlite:///:memory:")


def test_first_upsert_creates_player_with_starter_pool() -> None:
    repo = _new_repo()
    player = repo.upsert_by_provider(
        provider_subject="google:abc",
        email="alice@example.com",
        name="Alice",
    )
    assert player.id
    assert player.provider_subject == "google:abc"
    assert player.email == "alice@example.com"
    assert player.elo == 1000
    assert set(player.unlocked_characters) == set(DEFAULT_STARTERS)
    assert isinstance(player.created_at, datetime)


def test_second_upsert_updates_existing_row() -> None:
    repo = _new_repo()
    first = repo.upsert_by_provider(
        provider_subject="google:abc", email=None, name=None
    )
    second = repo.upsert_by_provider(
        provider_subject="google:abc",
        email="alice@example.com",
        name="Alice",
    )
    assert first.id == second.id  # same row
    assert second.email == "alice@example.com"
    assert second.name == "Alice"
    assert second.last_seen is not None and second.last_seen >= first.last_seen  # type: ignore[operator]


def test_get_unknown_id_raises_keyerror() -> None:
    repo = _new_repo()
    try:
        repo.get("does-not-exist")
    except KeyError:
        return
    raise AssertionError("expected KeyError")


def test_get_known_id_returns_player() -> None:
    repo = _new_repo()
    created = repo.upsert_by_provider(
        provider_subject="google:xyz", email=None, name=None
    )
    fetched = repo.get(created.id)
    assert fetched.provider_subject == "google:xyz"
