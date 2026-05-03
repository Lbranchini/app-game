"""Confirms the rate limiter is wired and the configured caps fire.

The limiter is keyed by remote address; under TestClient that's 127.0.0.1,
so all calls from one client share the same bucket.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agora.interfaces.api.main import create_app
from agora.interfaces.api.rate_limit import limiter


@pytest.fixture
def client() -> TestClient:
    # Each test gets a fresh app + reset limiter so buckets don't leak.
    limiter.reset()
    return TestClient(create_app())


def test_dev_token_returns_429_after_burst(client: TestClient) -> None:
    """`/auth/dev-token` is capped at 30/minute. The 31st call should 429."""
    last_status = 200
    for _ in range(35):
        last_status = client.post("/auth/dev-token").status_code
        if last_status == 429:
            break
    assert last_status == 429


def test_health_endpoint_is_not_rate_limited_at_burst(client: TestClient) -> None:
    """The default 120/minute on unannotated routes shouldn't trip in normal play."""
    statuses = [client.get("/health").status_code for _ in range(20)]
    assert all(s == 200 for s in statuses)


def test_dev_match_start_eventually_caps(client: TestClient) -> None:
    """`/match/dev/start` is capped at 30/minute even with valid input."""
    body = {
        "team_a": ["achilles", "athena", "anubis"],
        "team_b": ["thor", "isis", "loki"],
        "arena_id": "neutral",
        "seed": 1,
    }
    last = 200
    for _ in range(35):
        last = client.post("/match/dev/start", json=body).status_code
        if last == 429:
            break
    assert last == 429
