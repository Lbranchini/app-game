"""Match history record.

Stored once a match finishes. Carries enough metadata for a recent-matches
screen and for ELO computations later.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MatchRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    arena_id: str
    side_a_player_id: str
    side_b_player_id: str
    team_a: list[str]
    team_b: list[str]
    winner: str | None  # "A" / "B" / None for draw
    turns: int
    seed: int = 0
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: datetime | None = None
    # Per-side ELO swing applied at match end. `None` for matches between
    # players that aren't in the persistence layer (dev_a / dev_b / etc.).
    elo_delta_a: int | None = None
    elo_delta_b: int | None = None
