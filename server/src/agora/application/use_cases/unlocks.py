"""Threshold-based character unlocks.

A small registry of rules evaluated after every finished match. Each rule
points at a single counter in `Player.progress` (e.g. `wins`,
`matches_played`) and a numeric threshold; richer rules can override
`predicate` directly.

Keeping the rule shape data-driven means the frontend can fetch the catalog
and render each rule as a progress bar without re-implementing the math.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from agora.application.ports import PlayerRepository
from agora.domain.player import Player


Predicate = Callable[[Player], bool]


@dataclass(frozen=True)
class UnlockRule:
    character_id: str
    description: str
    progress_key: str | None = None
    target: int | None = None
    predicate: Predicate | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        # Either threshold form OR a custom predicate must be present.
        if self.predicate is None and (self.progress_key is None or self.target is None):
            raise ValueError(
                f"Rule for {self.character_id} needs progress_key + target or a predicate"
            )

    def is_satisfied(self, player: Player) -> bool:
        if self.predicate is not None:
            return self.predicate(player)
        assert self.progress_key is not None and self.target is not None
        return player.progress.get(self.progress_key, 0) >= self.target

    def progress_for(self, player: Player) -> tuple[int, int] | None:
        """Return `(current, target)` if this rule is threshold-based, else None."""
        if self.progress_key is None or self.target is None:
            return None
        return player.progress.get(self.progress_key, 0), self.target


DEFAULT_RULES: tuple[UnlockRule, ...] = (
    UnlockRule(
        character_id="medusa",
        description="Win 5 ranked matches",
        progress_key="wins",
        target=5,
    ),
    UnlockRule(
        character_id="sun_wukong",
        description="Win 10 ranked matches",
        progress_key="wins",
        target=10,
    ),
    UnlockRule(
        character_id="mulan",
        description="Win 25 ranked matches",
        progress_key="wins",
        target=25,
    ),
    UnlockRule(
        character_id="amaterasu",
        description="Play 50 matches (any outcome)",
        progress_key="matches_played",
        target=50,
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

    @property
    def rules(self) -> tuple[UnlockRule, ...]:
        return self._rules

    def apply(self, player_id: str) -> list[str]:
        """Return the list of newly-unlocked character ids."""
        player = self._players.get(player_id)
        owned = set(player.unlocked_characters)
        newly: list[str] = []
        for rule in self._rules:
            if rule.character_id in owned:
                continue
            if rule.is_satisfied(player):
                owned.add(rule.character_id)
                newly.append(rule.character_id)
        if newly:
            self._players.update_unlocked(player_id, sorted(owned))
        return newly
