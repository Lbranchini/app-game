"""Use case: create the initial match state."""

from __future__ import annotations

from agora.application.ports import RandomSource
from agora.domain.character import Character
from agora.domain.enums import Essence, ROLLABLE_ESSENCES, Side
from agora.domain.match import CharacterState, MatchState, PlayerState


def start_match(
    match_id: str,
    player_a_id: str,
    team_a: list[Character],
    player_b_id: str,
    team_b: list[Character],
    rng: RandomSource,
    seed: int = 0,
) -> MatchState:
    """Create the initial state. Side A starts with 1 essence; B starts with 3."""
    if len(team_a) != 3 or len(team_b) != 3:
        raise ValueError("Each team must have exactly 3 characters")

    state = MatchState(
        match_id=match_id,
        a=PlayerState(
            id=player_a_id,
            side=Side.A,
            characters=[_new_character_state(c) for c in team_a],
        ),
        b=PlayerState(
            id=player_b_id,
            side=Side.B,
            characters=[_new_character_state(c) for c in team_b],
        ),
        rng_seed=seed,
    )
    _generate_essences(state.a, 1, rng)
    _generate_essences(state.b, 3, rng)
    return state


def _new_character_state(character: Character) -> CharacterState:
    return CharacterState(
        id=character.id,
        name=character.name,
        hp=character.base_hp,
        hp_max=character.base_hp,
    )


def _generate_essences(player: PlayerState, count: int, rng: RandomSource) -> None:
    options = [e.value for e in ROLLABLE_ESSENCES]
    for _ in range(count):
        chosen = Essence(rng.choice(options))
        player.essences[chosen] = player.essences.get(chosen, 0) + 1
