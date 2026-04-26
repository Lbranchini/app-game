"""Resolution context passed to every handler.

A plain dataclass with mutable fields. Handlers read and write through it so
they don't need to know about the orchestrator.
"""

from __future__ import annotations

from dataclasses import dataclass

from agora.application.ports import RandomSource
from agora.domain.events import Event
from agora.domain.match import CharacterState, MatchState, PlayerState


@dataclass
class EffectContext:
    state: MatchState
    source: CharacterState
    target: CharacterState
    target_owner: PlayerState
    rng: RandomSource
    events: list[Event]
