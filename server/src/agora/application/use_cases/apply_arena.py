"""Apply arena modifiers to match state.

The engine handles a known subset of modifier kinds. Unknown kinds are
ignored silently so new arenas can be authored ahead of engine support.
"""

from __future__ import annotations

from agora.domain.arena import Arena
from agora.domain.enums import Side
from agora.domain.match import ActiveStatus, MatchState, PlayerState

KNOWN_MATCH_START_KINDS = frozenset({"hp_boost_by_mythology", "apply_status_at_start"})


def apply_match_start(state: MatchState, arena: Arena, mythology_by_id: dict[str, str]) -> None:
    """Mutate `state` with arena modifiers that fire at match start."""
    for modifier in arena.modifiers:
        if modifier.kind == "hp_boost_by_mythology":
            target_mythology = (modifier.mythology or "").lower()
            for player in (state.a, state.b):
                for character in player.characters:
                    char_myth = mythology_by_id.get(character.id, "").lower()
                    if char_myth == target_mythology:
                        character.hp_max += modifier.value
                        character.hp += modifier.value
        elif modifier.kind == "apply_status_at_start":
            if modifier.status is None:
                continue
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
        # Unknown kinds: silently ignored (forward-compatible).


def _targeted_players(state: MatchState, target: str) -> list[PlayerState]:
    if target == "side_a":
        return [state.a]
    if target == "side_b":
        return [state.b]
    return [state.a, state.b]


def mythology_index(characters: dict[str, object]) -> dict[str, str]:
    """Build a {character_id -> mythology} lookup from the character repository."""
    out: dict[str, str] = {}
    for cid, character in characters.items():
        myth = getattr(character, "mythology", None)
        if isinstance(myth, str):
            out[cid] = myth
    return out
