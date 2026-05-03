"""Mutable match state."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from agora.domain.enums import Essence, Side

EssencePool = dict[Essence, int]


def _empty_essence_pool() -> EssencePool:
    return {e: 0 for e in Essence if e is not Essence.GENERIC}


class ActiveStatus(BaseModel):
    """A status currently applied to a character in-match."""

    model_config = ConfigDict(extra="forbid")

    name: str
    duration: int
    value: int = 0
    source: str | None = None  # character id that applied it


class CharacterState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    hp: int
    hp_max: int
    cooldowns: dict[str, int] = Field(default_factory=dict)
    statuses: list[ActiveStatus] = Field(default_factory=list)
    shield: int = 0
    shield_source: str | None = None  # character id that applied the active shield

    @property
    def alive(self) -> bool:
        return self.hp > 0


class PlayerState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    side: Side
    characters: list[CharacterState]
    essences: EssencePool = Field(default_factory=_empty_essence_pool)

    @property
    def defeated(self) -> bool:
        return all(not c.alive for c in self.characters)


class MatchState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    match_id: str
    arena_id: str = "neutral"
    turn: int = 1
    current_side: Side = Side.A
    a: PlayerState
    b: PlayerState
    rng_seed: int = 0
    finished: bool = False
    winner: Side | None = None
    # Server-authoritative timer. `turn_deadline` is the wall-clock instant
    # after which the active side's turn auto-resolves with whatever they've
    # submitted (or an empty queue). The runtime updates this on every
    # advance; the engine itself doesn't read it.
    turn_deadline: datetime | None = None

    def player(self, side: Side) -> PlayerState:
        return self.a if side is Side.A else self.b

    def opponent(self, side: Side) -> PlayerState:
        return self.b if side is Side.A else self.a


class Action(BaseModel):
    """A skill use submitted by a player for the current turn."""

    model_config = ConfigDict(extra="forbid")

    character_id: str
    skill_id: str
    target_ids: list[str] = Field(default_factory=list)
    paid: dict[Essence, int] = Field(default_factory=dict)
