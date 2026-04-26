"""Ports (interfaces) the application layer depends on.

Infrastructure provides the concrete implementations.
"""

from __future__ import annotations

from typing import Protocol

from agora.domain.arena import Arena
from agora.domain.character import Character


class CharacterRepository(Protocol):
    """Source of character definitions."""

    def get(self, character_id: str) -> Character: ...
    def all(self) -> dict[str, Character]: ...


class ArenaRepository(Protocol):
    """Source of arena definitions."""

    def get(self, arena_id: str) -> Arena: ...
    def all(self) -> dict[str, Arena]: ...


class RandomSource(Protocol):
    """Deterministic random source.

    A given seed must produce identical sequences across calls — required for
    replays and reproducible balance simulations.
    """

    def choice(self, options: list[str]) -> str: ...
    def randint(self, lo: int, hi: int) -> int: ...
