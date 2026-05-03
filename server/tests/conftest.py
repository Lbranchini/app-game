"""Shared test fixtures."""

from __future__ import annotations

import pytest

from agora.domain.character import Character
from agora.infrastructure.yaml_repository import YamlCharacterRepository
from agora.interfaces.api import metrics as _metrics
from agora.interfaces.api.rate_limit import limiter


@pytest.fixture(autouse=True)
def _reset_rate_limit_buckets() -> None:
    """Per-IP buckets persist across tests since slowapi caches them on the
    Limiter instance. Reset before every test so a chatty test doesn't
    exhaust the cap and 429 a later one."""
    limiter.reset()


@pytest.fixture(autouse=True)
def _reset_prometheus_metrics() -> None:
    """Counters/gauges live on a process-global registry. For tests we zero
    the gauges via `set` and zero unlabelled counters by reaching into
    `_value` (Prometheus deliberately doesn't expose a public reset for
    monotonic counters). Labelled counters use `clear()` which is the
    documented way to drop seen label combinations."""
    _metrics.active_matches.set(0)
    _metrics.matchmaking_queue_depth.set(0)
    _metrics.matches_finished_total.clear()
    _metrics.matches_forfeited_total._value.set(0)  # type: ignore[attr-defined]


@pytest.fixture(scope="session")
def repository() -> YamlCharacterRepository:
    return YamlCharacterRepository()


@pytest.fixture(scope="session")
def all_characters(repository: YamlCharacterRepository) -> dict[str, Character]:
    return repository.all()


@pytest.fixture
def achilles(all_characters: dict[str, Character]) -> Character:
    return all_characters["achilles"]


@pytest.fixture
def athena(all_characters: dict[str, Character]) -> Character:
    return all_characters["athena"]


@pytest.fixture
def anubis(all_characters: dict[str, Character]) -> Character:
    return all_characters["anubis"]
