"""Mission progress — per-player counters updated after every match.

This is the foundation for the unlock catalog described in
`docs/09-missions.md`. Today the service only records the most universal
counters (`wins`, `losses`, `draws`, `matches_played`); individual mission
rules will read from the same `Player.progress` map and check thresholds.
"""

from __future__ import annotations

from agora.application.ports import PlayerRepository
from agora.domain.player import Player


class MissionService:
    def __init__(self, players: PlayerRepository) -> None:
        self._players = players

    def record_match_outcome(
        self,
        *,
        side_a_subject: str,
        side_b_subject: str,
        winner: str | None,
    ) -> None:
        """Increment win/loss/draw counters for each side's underlying Player.

        Subjects that don't resolve to a real player row (e.g. dev_a / dev_b)
        are silently skipped — same posture as the ELO update path.
        """
        side_a_player = self._players.get_by_provider(side_a_subject)
        side_b_player = self._players.get_by_provider(side_b_subject)

        if side_a_player is not None:
            self._bump(side_a_player, won=winner == "A", lost=winner == "B")
        if side_b_player is not None:
            self._bump(side_b_player, won=winner == "B", lost=winner == "A")

    def _bump(self, player: Player, *, won: bool, lost: bool) -> None:
        progress = dict(player.progress)
        progress["matches_played"] = progress.get("matches_played", 0) + 1
        if won:
            progress["wins"] = progress.get("wins", 0) + 1
        elif lost:
            progress["losses"] = progress.get("losses", 0) + 1
        else:
            progress["draws"] = progress.get("draws", 0) + 1
        self._players.update_progress(player.id, progress)
