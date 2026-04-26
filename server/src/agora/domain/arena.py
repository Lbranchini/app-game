"""Arena definition: a global modifier set applied for one match."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from agora.domain.enums import DamageClass, Essence, SkillKind


class ArenaModifier(BaseModel):
    """One global rule the arena imposes on the match.

    The engine handles a known subset of `kind` values; unknown kinds are
    accepted and ignored so new arenas can be authored ahead of engine support.
    """

    model_config = ConfigDict(extra="forbid")

    kind: str
    mythology: str | None = None
    status: str | None = None
    duration: int = 0
    value: int = 0
    multiplier: float = 1.0
    essence: Essence | None = None
    target: Literal["all", "side_a", "side_b"] = "all"
    damage_class: DamageClass | None = None
    skill_kind: SkillKind | None = None
    start_turn: int = 1
    every: int = 1


class Arena(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str
    modifiers: list[ArenaModifier] = Field(default_factory=list)
