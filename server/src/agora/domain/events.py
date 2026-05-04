"""Domain events emitted while resolving a turn (for replay and telemetry)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EventKind = Literal[
    "skill_used",
    "damage",
    "heal",
    "status_applied",
    "status_expired",
    "character_defeated",
    "essence_generated",
    "essence_drained",
    "turn_started",
    "turn_ended",
    "match_finished",
    "invalid_action",
    # Emitted by `MatchRuntime` when a player's reconnect grace expires.
    "forfeit",
    # Emitted by the engine when a character borrows / loses a copied skill
    # via the `copy` effect. See `domain.match.GrantedSkill`.
    "skill_granted",
    "skill_expired",
]


class Event(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: EventKind
    details: dict[str, object] = Field(default_factory=dict)
