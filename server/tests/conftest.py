"""Shared test fixtures."""

from __future__ import annotations

import pytest

from agora.domain.character import Character
from agora.infrastructure.yaml_repository import YamlCharacterRepository
from agora.interfaces.api.rate_limit import limiter


@pytest.fixture(autouse=True)
def _reset_rate_limit_buckets() -> None:
    """Per-IP buckets persist across tests since slowapi caches them on the
    Limiter instance. Reset before every test so a chatty test doesn't
    exhaust the cap and 429 a later one."""
    limiter.reset()


@pytest.fixture(scope="session")
def repository() -> YamlCharacterRepository:
    return YamlCharacterRepository()


@pytest.fixture(scope="session")
def all_characters(repository: YamlCharacterRepository) -> dict[str, Character]:
    return repository.all()


@pytest.fixture
def achilles(all_characters: dict[str, Character]) -> Character:
    return all_characters["achilles"]


@pytest.fixture
def athena(all_characters: dict[str, Character]) -> Character:
    return all_characters["athena"]


@pytest.fixture
def anubis(all_characters: dict[str, Character]) -> Character:
    return all_characters["anubis"]
