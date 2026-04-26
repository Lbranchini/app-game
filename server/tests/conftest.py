"""Fixtures compartilhadas dos testes."""

from __future__ import annotations

import pytest

from agora.data_loader import load_all_characters
from agora.schemas import Personagem


@pytest.fixture(scope="session")
def all_characters() -> dict[str, Personagem]:
    return load_all_characters()


@pytest.fixture
def aquiles(all_characters: dict[str, Personagem]) -> Personagem:
    return all_characters["aquiles"]


@pytest.fixture
def atena(all_characters: dict[str, Personagem]) -> Personagem:
    return all_characters["atena"]


@pytest.fixture
def anubis(all_characters: dict[str, Personagem]) -> Personagem:
    return all_characters["anubis"]
