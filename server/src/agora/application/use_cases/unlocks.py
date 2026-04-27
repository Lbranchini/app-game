"""Threshold-based character unlocks.

A small registry of `(character_id -> rule)` pairs evaluated after every
finished match. Rules read from `Player.progress` so adding a new rule that
references existing counters (wins, total_damage_dealt, status_applied.X)
requires no engine changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from agora.application.ports import PlayerRepository
from agora.domain.player import Player


Rule = Callable[[Player], bool]


@dataclass(frozen=True)
class UnlockRule:
    character_id: str
    description: str
    predicate: Rule


# Small starter catalog. The full design lives in docs/09-missions.md;
# every character there gets three thematic mission rules. For now we ship
# a tight set keyed off the universal `wins` counter and grow from here.
DEFAULT_RULES: tuple[UnlockRule, ...] = (
    UnlockRule(
        character_id="medusa",
        description="Win 5 ranked matches",
        predicate=lambda p: p.progress.get("wins", 0) >= 5,
    ),
    UnlockRule(
        character_id="sun_wukong",
        description="Win 10 ranked matches",
        predicate=lambda p: p.progress.get("wins", 0) >= 10,
    ),
    UnlockRule(
        character_id="mulan",
        description="Win 25 ranked matches",
        predicate=lambda p: p.progress.get("wins", 0) >= 25,
    ),
    UnlockRule(
        character_id="amaterasu",
        description="Play 50 matches (any outcome)",
        predicate=lambda p: p.progress.get("matches_played", 0) >= 50,
    ),
)


class UnlockService:
    """Evaluates the catalog and writes any new unlocks back to the repo.

    Idempotent — characters already in the player's roster are left alone,
    so it's safe to call after every match.
    """

    def __init__(
        self,
        players: PlayerRepository,
        rules: tuple[UnlockRule, ...] = DEFAULT_RULES,
    ) -> None:
        self._players = players
        self._rules = rules

    def apply(self, player_id: str) -> list[str]:
        """Return the list of newly-unlocked character ids."""
        player = self._players.get(player_id)
        owned = set(player.unlocked_characters)
        newly: list[str] = []
        for rule in self._rules:
            if rule.character_id in owned:
                continue
            if rule.predicate(player):
                owned.add(rule.character_id)
                newly.append(rule.character_id)
        if newly:
            self._players.update_unlocked(player_id, sorted(owned))
        return newly
