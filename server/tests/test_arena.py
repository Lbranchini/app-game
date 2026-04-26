"""Tests for arena modifiers wiring into start_match."""

from __future__ import annotations

import pytest

from agora.application.ports import CharacterRepository, RandomSource
from agora.application.use_cases import start_match
from agora.domain.character import Character
from agora.infrastructure.seeded_random import SeededRandom
from agora.infrastructure.yaml_arena_repository import YamlArenaRepository


@pytest.fixture(scope="session")
def arenas() -> YamlArenaRepository:
    return YamlArenaRepository()


@pytest.fixture
def rng() -> RandomSource:
    return SeededRandom(42)


def _start(
    *,
    repository: CharacterRepository,
    chars: dict[str, Character],
    arena_id: str,
    arenas: YamlArenaRepository,
    rng: RandomSource,
) -> object:
    arena = arenas.get(arena_id)
    return start_match(
        match_id="m",
        player_a_id="p1",
        team_a=[chars["achilles"], chars["athena"], chars["anubis"]],
        player_b_id="p2",
        team_b=[chars["achilles"], chars["athena"], chars["anubis"]],
        rng=rng,
        seed=42,
        arena=arena,
    )


def test_neutral_arena_has_no_effect(
    repository: CharacterRepository,
    all_characters: dict[str, Character],
    arenas: YamlArenaRepository,
    rng: RandomSource,
) -> None:
    state = _start(
        repository=repository, chars=all_characters, arena_id="neutral",
        arenas=arenas, rng=rng,
    )
    assert state.arena_id == "neutral"
    assert state.a.characters[0].hp_max == 110  # Achilles base
    assert all(not c.statuses for c in state.a.characters)


def test_olympus_buffs_greek_hp(
    repository: CharacterRepository,
    all_characters: dict[str, Character],
    arenas: YamlArenaRepository,
    rng: RandomSource,
) -> None:
    state = _start(
        repository=repository, chars=all_characters, arena_id="olympus",
        arenas=arenas, rng=rng,
    )
    achilles = state.a.characters[0]
    athena = state.a.characters[1]
    anubis = state.a.characters[2]
    assert achilles.hp_max == 115 and achilles.hp == 115  # Greek +5
    assert athena.hp_max == 100 and athena.hp == 100      # Greek +5 (base 95)
    assert anubis.hp_max == 95 and anubis.hp == 95         # Egyptian, untouched


def test_underworld_applies_poison_to_everyone(
    repository: CharacterRepository,
    all_characters: dict[str, Character],
    arenas: YamlArenaRepository,
    rng: RandomSource,
) -> None:
    state = _start(
        repository=repository, chars=all_characters, arena_id="underworld",
        arenas=arenas, rng=rng,
    )
    for player in (state.a, state.b):
        for character in player.characters:
            statuses = [s for s in character.statuses if s.name == "poison"]
            assert len(statuses) == 1
            assert statuses[0].value == 5
            assert statuses[0].duration == 3
