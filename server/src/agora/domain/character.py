"""Character and skill definitions (immutable, loaded from data files)."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from agora.domain.enums import (
    Archetype,
    DamageClass,
    EffectKind,
    Essence,
    SkillKind,
    TargetKind,
)

EssenceCost = dict[Essence, int]


class Effect(BaseModel):
    """One atomic effect applied when a skill resolves on a target."""

    model_config = ConfigDict(extra="forbid")

    kind: EffectKind
    value: int = 0
    duration: int = 0
    damage_class: DamageClass | None = None
    status: str | None = None
    piercing: bool = False
    true: bool = False  # ignores invulnerability


class Skill(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    kind: SkillKind
    cost: EssenceCost = Field(default_factory=dict)
    cooldown: Annotated[int, Field(ge=0)] = 0
    duration: Annotated[int, Field(ge=0)] = 0
    target: TargetKind
    effects: list[Effect]
    description: str = ""


class Character(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    mythology: str
    archetype: Archetype
    base_hp: Annotated[int, Field(ge=50, le=200)]
    description: str | None = None
    skills: list[Skill]
