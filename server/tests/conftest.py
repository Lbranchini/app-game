"""Shared test fixtures."""

from __future__ import annotations

import pytest

from agora.domain.character import Character
from agora.infrastructure.yaml_repository import YamlCharacterRepository


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
