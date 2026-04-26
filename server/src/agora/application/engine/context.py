"""Resolution contexts passed to handlers.

Plain dataclasses with mutable fields. Handlers read and write through them
so they don't need to know about the orchestrator.
"""

from __future__ import annotations

from dataclasses import dataclass

from agora.application.ports import RandomSource
from agora.domain.events import Event
from agora.domain.match import ActiveStatus, CharacterState, MatchState, PlayerState


@dataclass
class EffectContext:
    state: MatchState
    source: CharacterState
    target: CharacterState
    target_owner: PlayerState
    rng: RandomSource
    events: list[Event]


@dataclass
class StatusTickContext:
    """Context passed to a `StatusTickHandler` once per turn.

    Carries the player so handlers can affect the essence pool (drained), and
    the rng so random selections (which essence to drop) stay seeded.
    """

    status: ActiveStatus
    character: CharacterState
    player: PlayerState
    rng: RandomSource
    events: list[Event]
