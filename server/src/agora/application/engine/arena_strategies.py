"""Polymorphic arena-modifier strategies.

Each `ArenaModifier.kind` maps to a strategy subclass implementing one or
more lifecycle hooks. Unknown kinds are silently ignored — modifiers can be
authored ahead of engine support.
"""

from __future__ import annotations

from abc import ABC

from agora.domain.arena import Arena, ArenaModifier
from agora.domain.enums import Side
from agora.domain.match import ActiveStatus, MatchState, PlayerState


class ArenaModifierStrategy(ABC):
    """Base strategy. Override only the hooks you need."""

    def apply_match_start(
        self,
        modifier: ArenaModifier,
        state: MatchState,
        *,
        mythology_index: dict[str, str],
    ) -> None: ...

    def apply_turn_start(self, modifier: ArenaModifier, state: MatchState) -> None: ...


class HpBoostByMythology(ArenaModifierStrategy):
    def apply_match_start(
        self,
        modifier: ArenaModifier,
        state: MatchState,
        *,
        mythology_index: dict[str, str],
    ) -> None:
        target_myth = (modifier.mythology or "").lower()
        for player in (state.a, state.b):
            for character in player.characters:
                actual = mythology_index.get(character.id, "").lower()
                if actual == target_myth:
                    character.hp_max += modifier.value
                    character.hp += modifier.value


class ApplyStatusAtStart(ArenaModifierStrategy):
    def apply_match_start(
        self,
        modifier: ArenaModifier,
        state: MatchState,
        *,
        mythology_index: dict[str, str],
    ) -> None:
        if modifier.status is None:
            return
        for player in _targeted_players(state, modifier.target):
            for character in player.characters:
                character.statuses.append(
                    ActiveStatus(
                        name=modifier.status,
                        duration=modifier.duration,
                        value=modifier.value,
                        source="arena",
                    )
                )


class _UnknownStrategy(ArenaModifierStrategy):
    """Silent no-op for modifier kinds the engine doesn't yet implement."""


_UNKNOWN = _UnknownStrategy()


STRATEGY_REGISTRY: dict[str, ArenaModifierStrategy] = {
    "hp_boost_by_mythology": HpBoostByMythology(),
    "apply_status_at_start": ApplyStatusAtStart(),
}


def strategy_for(modifier: ArenaModifier) -> ArenaModifierStrategy:
    return STRATEGY_REGISTRY.get(modifier.kind, _UNKNOWN)


def _targeted_players(state: MatchState, target: str) -> list[PlayerState]:
    if target == "side_a":
        return [state.a]
    if target == "side_b":
        return [state.b]
    return [state.a, state.b]


def apply_arena_match_start(
    arena: Arena | None,
    state: MatchState,
    mythology_index: dict[str, str],
) -> None:
    if arena is None:
        return
    for modifier in arena.modifiers:
        strategy_for(modifier).apply_match_start(
            modifier, state, mythology_index=mythology_index
        )


def apply_arena_turn_start(
    arena: Arena | None,
    state: MatchState,
) -> None:
    if arena is None:
        return
    for modifier in arena.modifiers:
        strategy_for(modifier).apply_turn_start(modifier, state)


# Re-export Side for callers that build mythology indices and need the type.
__all__ = [
    "ArenaModifierStrategy",
    "HpBoostByMythology",
    "ApplyStatusAtStart",
    "STRATEGY_REGISTRY",
    "Side",
    "apply_arena_match_start",
    "apply_arena_turn_start",
    "strategy_for",
]
