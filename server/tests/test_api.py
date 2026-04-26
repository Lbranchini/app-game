"""Smoke tests for the FastAPI surface."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agora.interfaces.api.main import create_app
from agora.interfaces.api.security import AuthenticatedUser, issue_access_token


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_characters_includes_achilles(client: TestClient) -> None:
    response = client.get("/characters")
    assert response.status_code == 200
    payload = response.json()
    ids = {c["id"] for c in payload}
    assert {"achilles", "athena", "anubis"}.issubset(ids)


def test_list_arenas_includes_olympus(client: TestClient) -> None:
    response = client.get("/arenas")
    assert response.status_code == 200
    ids = {a["id"] for a in response.json()}
    assert {"neutral", "olympus", "underworld"}.issubset(ids)


def test_google_login_returns_501_without_credentials(client: TestClient) -> None:
    response = client.get("/auth/google/login")
    assert response.status_code == 501


def test_dev_token_then_me_returns_user(client: TestClient) -> None:
    token_response = client.post("/auth/dev-token")
    assert token_response.status_code == 200
    token = token_response.json()["access_token"]

    me_response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    assert me_response.json()["sub"] == "dev:local"


def test_me_without_token_is_unauthorized(client: TestClient) -> None:
    response = client.get("/auth/me")
    assert response.status_code in (401, 403)


def test_issue_access_token_round_trip() -> None:
    user = AuthenticatedUser(sub="x:1", email="a@b.com", name="A")
    token = issue_access_token(user)
    assert isinstance(token, str)
    assert token.count(".") == 2  # JWT shape
