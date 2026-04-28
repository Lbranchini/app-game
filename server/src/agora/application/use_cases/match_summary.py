"""Build a per-side telemetry summary from the engine's event stream.

Pure function — takes the events emitted across the whole match and the two
team rosters, returns aggregated counters mission rules can consume. No
storage, no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from agora.domain.events import Event


@dataclass
class MatchSummary:
    winner: str | None
    damage_dealt_by_a: int = 0
    damage_dealt_by_b: int = 0
    damage_taken_by_a: int = 0
    damage_taken_by_b: int = 0
    healing_done_by_a: int = 0
    healing_done_by_b: int = 0
    status_applied_by_a: dict[str, int] = field(default_factory=dict)
    status_applied_by_b: dict[str, int] = field(default_factory=dict)


def summarize_events(
    events: Iterable[Event],
    *,
    team_a: list[str],
    team_b: list[str],
    winner: str | None,
) -> MatchSummary:
    a_set = set(team_a)
    b_set = set(team_b)
    summary = MatchSummary(winner=winner)

    for event in events:
        details = event.details or {}
        if event.kind == "damage":
            value = _coerce_int(details.get("value"))
            source = details.get("source")
            target = details.get("target")
            if isinstance(source, str) and source in a_set:
                summary.damage_dealt_by_a += value
            elif isinstance(source, str) and source in b_set:
                summary.damage_dealt_by_b += value
            if isinstance(target, str) and target in a_set:
                summary.damage_taken_by_a += value
            elif isinstance(target, str) and target in b_set:
                summary.damage_taken_by_b += value

        elif event.kind == "heal":
            value = _coerce_int(details.get("value"))
            source = details.get("source")
            if isinstance(source, str) and source in a_set:
                summary.healing_done_by_a += value
            elif isinstance(source, str) and source in b_set:
                summary.healing_done_by_b += value

        elif event.kind == "status_applied":
            source = details.get("source")
            status = details.get("status")
            if not isinstance(source, str) or not isinstance(status, str):
                continue
            if source in a_set:
                summary.status_applied_by_a[status] = (
                    summary.status_applied_by_a.get(status, 0) + 1
                )
            elif source in b_set:
                summary.status_applied_by_b[status] = (
                    summary.status_applied_by_b.get(status, 0) + 1
                )

    return summary


def _coerce_int(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0
