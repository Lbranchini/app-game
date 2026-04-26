"""Use case: resolve a single turn for the current side.

Thin wrapper around `MatchEngine`. Re-exports the dodge skill so callers and
tests don't need to reach into the engine package directly.
"""

from __future__ import annotations

from agora.application.engine import MatchEngine
from agora.application.engine.match_engine import DODGE_SKILL, DODGE_SKILL_ID
from agora.application.ports import CharacterRepository, RandomSource
from agora.domain.events import Event
from agora.domain.match import Action, MatchState


def resolve_turn(
    state: MatchState,
    actions: list[Action],
    repository: CharacterRepository,
    rng: RandomSource,
) -> tuple[MatchState, list[Event]]:
    return MatchEngine(characters=repository, rng=rng).resolve_turn(state, actions)


__all__ = ["DODGE_SKILL", "DODGE_SKILL_ID", "resolve_turn"]
