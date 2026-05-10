"""Stable error codes on the HTTP envelope.

`raise_api_error(...)` ships a structured detail dict that the
exception handler in `main.py` unpacks into the public `ErrorResponse`
shape: every error a route raises is identified by a machine `code`
the client localizes via `t("error.<code>")`. Plain
`raise HTTPException(detail="...")` still works as a fallback path
keyed by `http_<status>`.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agora.interfaces.api.main import create_app
from agora.interfaces.api.routers import match as match_router


@pytest.fixture
def client() -> TestClient:
    match_router._runtime = None
    return TestClient(create_app())


def test_match_not_found_carries_stable_code(client: TestClient) -> None:
    resp = client.get("/match/does-not-exist")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == "match.not_found"
    assert body["message"] == "match not found"
    # Vars surface on `details` so a client could render
    # "match {{match_id}} not found" with the missing id.
    assert body["details"] == {"match_id": "does-not-exist"}


def test_character_not_found_carries_stable_code(client: TestClient) -> None:
    resp = client.get("/characters/does-not-exist")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == "character.not_found"
    assert body["details"] == {"character_id": "does-not-exist"}


def test_arena_not_found_carries_stable_code(client: TestClient) -> None:
    resp = client.get("/arenas/does-not-exist")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == "arena.not_found"
    assert body["details"] == {"arena_id": "does-not-exist"}


def test_dev_start_bad_team_size_carries_stable_code(client: TestClient) -> None:
    resp = client.post(
        "/match/dev/start",
        json={"team_a": ["achilles"], "team_b": ["thor", "isis", "loki"]},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == "match.bad_team_size"
    assert body["details"] == {"team_a": 1, "team_b": 3}


def test_unauthenticated_me_falls_back_to_http_status_code(client: TestClient) -> None:
    """`/auth/me` without a token bubbles up FastAPI's bare 401, which
    still flows through the unified envelope as `http_401`."""
    resp = client.get("/auth/me")
    assert resp.status_code == 401
    body = resp.json()
    assert body["code"].startswith("http_")
    assert body["message"] != ""


def test_google_login_without_redirect_uri_carries_stable_code(
    client: TestClient,
) -> None:
    resp = client.get("/auth/google/login", follow_redirects=False)
    assert resp.status_code == 501
    body = resp.json()
    # The default settings don't ship a Google redirect URI, so this
    # is the first guard the route hits.
    assert body["code"] == "auth.google.redirect_uri_missing"


def test_apple_callback_without_config_carries_stable_code(client: TestClient) -> None:
    resp = client.post("/auth/apple/callback", data={"code": "anything"})
    assert resp.status_code == 501
    body = resp.json()
    assert body["code"] == "auth.apple.not_configured"
