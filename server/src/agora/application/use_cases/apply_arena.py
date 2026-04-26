"""Backwards-compatible facade over the engine's arena strategies."""

from __future__ import annotations

from agora.application.engine.arena_strategies import apply_arena_match_start
from agora.domain.arena import Arena
from agora.domain.match import MatchState


def apply_match_start(
    state: MatchState, arena: Arena, mythology_by_id: dict[str, str]
) -> None:
    apply_arena_match_start(arena, state, mythology_by_id)


def mythology_index(characters: dict[str, object]) -> dict[str, str]:
    out: dict[str, str] = {}
    for cid, character in characters.items():
        myth = getattr(character, "mythology", None)
        if isinstance(myth, str):
            out[cid] = myth
    return out
