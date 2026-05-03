"""Prometheus metrics exposed at `/metrics`.

Single module so anywhere we need to bump a counter we import the
specific metric, not the registry. The runtime + matchmaking service
update gauges/counters in line with their existing logging events; the
metrics + logs stay in sync that way.
"""

from __future__ import annotations

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

# ──────────────────────────────────────────────────────────────────────────
# Match lifecycle
# ──────────────────────────────────────────────────────────────────────────

active_matches = Gauge(
    "agora_active_matches",
    "In-memory matches the runtime currently tracks.",
)

matches_finished_total = Counter(
    "agora_matches_finished_total",
    "Matches that reached a final state, by winner side.",
    labelnames=("winner",),
)

matches_forfeited_total = Counter(
    "agora_matches_forfeited_total",
    "Matches that ended via the disconnect grace forfeit path.",
)

turn_resolve_seconds = Histogram(
    "agora_turn_resolve_seconds",
    "Time spent inside `MatchEngine.resolve_turn()` per resolved turn.",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

# ──────────────────────────────────────────────────────────────────────────
# Matchmaking
# ──────────────────────────────────────────────────────────────────────────

matchmaking_queue_depth = Gauge(
    "agora_matchmaking_queue_depth",
    "Players currently waiting in the ELO-based queue.",
)


def render_latest() -> tuple[bytes, str]:
    """Snapshot of every metric in Prometheus text format + content type."""
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
