"""Use case: create the initial match state.

Thin wrapper around `MatchEngine` for callers that only need a single call.
"""

from __future__ import annotations

from agora.application.engine import MatchEngine
from agora.application.ports import RandomSource
from agora.domain.arena import Arena
from agora.domain.character import Character
from agora.domain.match import MatchState


def start_match(
    match_id: str,
    player_a_id: str,
    team_a: list[Character],
    player_b_id: str,
    team_b: list[Character],
    rng: RandomSource,
    seed: int = 0,
    arena: Arena | None = None,
) -> MatchState:
    engine = MatchEngine(characters=_NullCharacterRepo(), rng=rng)
    return engine.start_match(
        match_id=match_id,
        player_a_id=player_a_id,
        team_a=team_a,
        player_b_id=player_b_id,
        team_b=team_b,
        seed=seed,
        arena=arena,
    )


class _NullCharacterRepo:
    """`start_match` only needs the rng + arena + the `Character` instances passed in.

    A no-op repository keeps the engine constructor uniform without forcing
    callers to provide one when they already have the characters in hand.
    """

    def get(self, character_id: str) -> Character:  # pragma: no cover
        raise KeyError(character_id)

    def all(self) -> dict[str, Character]:  # pragma: no cover
        return {}
