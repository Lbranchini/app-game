"""Reusable dependency providers."""

from __future__ import annotations

from functools import lru_cache

from agora.application.ports import ArenaRepository, CharacterRepository, PlayerRepository
from agora.infrastructure.sqlalchemy_player_repository import SqlAlchemyPlayerRepository
from agora.infrastructure.yaml_arena_repository import YamlArenaRepository
from agora.infrastructure.yaml_repository import YamlCharacterRepository
from agora.interfaces.api.settings import get_settings


@lru_cache(maxsize=1)
def get_character_repository() -> CharacterRepository:
    return YamlCharacterRepository()


@lru_cache(maxsize=1)
def get_arena_repository() -> ArenaRepository:
    return YamlArenaRepository()


@lru_cache(maxsize=1)
def get_player_repository() -> PlayerRepository:
    return SqlAlchemyPlayerRepository(database_url=get_settings().database_url)
