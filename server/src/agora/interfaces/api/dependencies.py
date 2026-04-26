"""Reusable dependency providers."""

from __future__ import annotations

from functools import lru_cache

from agora.application.ports import ArenaRepository, CharacterRepository
from agora.infrastructure.yaml_arena_repository import YamlArenaRepository
from agora.infrastructure.yaml_repository import YamlCharacterRepository


@lru_cache(maxsize=1)
def get_character_repository() -> CharacterRepository:
    return YamlCharacterRepository()


@lru_cache(maxsize=1)
def get_arena_repository() -> ArenaRepository:
    return YamlArenaRepository()
