"""Mission progress — per-player counters updated after every match.

Foundation for the unlock catalog described in `docs/09-missions.md`. The
service writes universal counters (matches_played, wins, losses, draws)
plus per-side telemetry pulled from a `MatchSummary`:

  * `total_damage_dealt`, `total_damage_taken`
  * `status_applied.<name>` — count of statuses that side applied to enemies

UnlockRule definitions read from the same `Player.progress` map.
"""

from __future__ import annotations

from agora.application.ports import PlayerRepository
from agora.application.use_cases.match_summary import MatchSummary
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
        summary: MatchSummary | None = None,
    ) -> None:
        """Increment counters for each side's underlying Player.

        Subjects that don't resolve to a real player row (e.g. `dev_a`/`dev_b`)
        are silently skipped — same posture as the ELO update path.
        """
        side_a_player = self._players.get_by_provider(side_a_subject)
        side_b_player = self._players.get_by_provider(side_b_subject)

        if side_a_player is not None:
            self._bump(
                side_a_player,
                won=winner == "A",
                lost=winner == "B",
                damage_dealt=summary.damage_dealt_by_a if summary else 0,
                damage_taken=summary.damage_taken_by_a if summary else 0,
                statuses_applied=summary.status_applied_by_a if summary else None,
            )
        if side_b_player is not None:
            self._bump(
                side_b_player,
                won=winner == "B",
                lost=winner == "A",
                damage_dealt=summary.damage_dealt_by_b if summary else 0,
                damage_taken=summary.damage_taken_by_b if summary else 0,
                statuses_applied=summary.status_applied_by_b if summary else None,
            )

    def _bump(
        self,
        player: Player,
        *,
        won: bool,
        lost: bool,
        damage_dealt: int = 0,
        damage_taken: int = 0,
        statuses_applied: dict[str, int] | None = None,
    ) -> None:
        progress = dict(player.progress)
        progress["matches_played"] = progress.get("matches_played", 0) + 1
        if won:
            progress["wins"] = progress.get("wins", 0) + 1
        elif lost:
            progress["losses"] = progress.get("losses", 0) + 1
        else:
            progress["draws"] = progress.get("draws", 0) + 1

        if damage_dealt:
            progress["total_damage_dealt"] = (
                progress.get("total_damage_dealt", 0) + damage_dealt
            )
        if damage_taken:
            progress["total_damage_taken"] = (
                progress.get("total_damage_taken", 0) + damage_taken
            )

        for name, count in (statuses_applied or {}).items():
            key = f"status_applied.{name}"
            progress[key] = progress.get(key, 0) + count

        self._players.update_progress(player.id, progress)
