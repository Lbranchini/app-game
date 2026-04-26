"""Pre-match ban-pick draft state (ranked-only)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from agora.domain.enums import Side


class DraftPhase(StrEnum):
    ARENA_REVEAL = "arena_reveal"
    BAN = "ban"
    PICK = "pick"
    CONFIRM = "confirm"
    DONE = "done"
    CANCELLED = "cancelled"


def _empty_bans() -> dict[Side, str | None]:
    return {Side.A: None, Side.B: None}


def _empty_picks() -> dict[Side, list[str]]:
    return {Side.A: [], Side.B: []}


def _default_pick_order() -> list[Side]:
    """Snake order for 3v3: A, B, B, A, A, B."""
    return [Side.A, Side.B, Side.B, Side.A, Side.A, Side.B]


class DraftState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft_id: str
    arena_id: str
    side_a_player_id: str
    side_b_player_id: str
    phase: DraftPhase = DraftPhase.ARENA_REVEAL
    bans: dict[Side, str | None] = Field(default_factory=_empty_bans)
    picks: dict[Side, list[str]] = Field(default_factory=_empty_picks)
    pick_order: list[Side] = Field(default_factory=_default_pick_order)
    pick_index: int = 0
    timer_deadline: datetime | None = None

    @property
    def picks_complete(self) -> bool:
        return self.pick_index >= len(self.pick_order)

    @property
    def current_picker(self) -> Side | None:
        if self.picks_complete:
            return None
        return self.pick_order[self.pick_index]
