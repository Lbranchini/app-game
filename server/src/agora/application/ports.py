"""Ports (interfaces) the application layer depends on.

Infrastructure provides the concrete implementations.
"""

from __future__ import annotations

from typing import Protocol

from agora.domain.arena import Arena
from agora.domain.character import Character
from agora.domain.player import Player


class CharacterRepository(Protocol):
    """Source of character definitions."""

    def get(self, character_id: str) -> Character: ...
    def all(self) -> dict[str, Character]: ...


class ArenaRepository(Protocol):
    """Source of arena definitions."""

    def get(self, arena_id: str) -> Arena: ...
    def all(self) -> dict[str, Arena]: ...


class PlayerRepository(Protocol):
    """Persistence port for player accounts.

    Implementations should be safe to call from a request handler — i.e. the
    SQLAlchemy implementation manages its own session lifecycle.
    """

    def upsert_by_provider(
        self, *, provider_subject: str, email: str | None, name: str | None
    ) -> Player: ...

    def get(self, player_id: str) -> Player: ...


class RandomSource(Protocol):
    """Deterministic random source.

    A given seed must produce identical sequences across calls — required for
    replays and reproducible balance simulations.
    """

    def choice(self, options: list[str]) -> str: ...
    def randint(self, lo: int, hi: int) -> int: ...
