"""Matchmaking — pairs queued players into a draft.

The MVP queue is FIFO: first two players to join are paired. Elo-based
brackets are a future improvement. The service is sync + in-process; a
production queue lives in Redis with the same external interface
(`join` / `leave` / `pop_pair`).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from agora.application.use_cases.draft import DraftService
from agora.domain.draft import DraftState


@dataclass
class QueuedPlayer:
    player_id: str  # provider subject (`google:1234`, etc.)
    display_name: str | None
    queued_at: datetime


class ArenaPicker(Protocol):
    def pick(self) -> str: ...


class RandomArenaPicker:
    def __init__(self, arena_ids: list[str]) -> None:
        if not arena_ids:
            raise ValueError("Need at least one arena")
        self._ids = list(arena_ids)
        self._rng = random.Random()

    def pick(self) -> str:
        return self._rng.choice(self._ids)


class MatchmakingService:
    """In-memory FIFO queue. Pairs the head two players into a fresh draft."""

    def __init__(self, draft_service: DraftService, arena_picker: ArenaPicker) -> None:
        self._draft_service = draft_service
        self._arenas = arena_picker
        self._queue: list[QueuedPlayer] = []

    # --------------------------------------------------------------------- #
    # Queue management                                                      #
    # --------------------------------------------------------------------- #

    def join(self, player_id: str, display_name: str | None = None) -> None:
        if any(p.player_id == player_id for p in self._queue):
            return
        self._queue.append(
            QueuedPlayer(
                player_id=player_id,
                display_name=display_name,
                queued_at=datetime.utcnow(),
            )
        )

    def leave(self, player_id: str) -> None:
        self._queue = [p for p in self._queue if p.player_id != player_id]

    def queued_player_ids(self) -> list[str]:
        return [p.player_id for p in self._queue]

    # --------------------------------------------------------------------- #
    # Pairing                                                               #
    # --------------------------------------------------------------------- #

    def try_pair(self) -> tuple[QueuedPlayer, QueuedPlayer, DraftState] | None:
        """If at least two players are queued, dequeue them and create a draft."""
        if len(self._queue) < 2:
            return None
        a = self._queue.pop(0)
        b = self._queue.pop(0)
        arena_id = self._arenas.pick()
        draft = self._draft_service.start(
            side_a_player_id=a.player_id,
            side_b_player_id=b.player_id,
            arena_id=arena_id,
        )
        return a, b, draft
