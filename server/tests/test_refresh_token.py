"""Refresh-token rotation + blacklist contract.

Covers issuance shape, single-use semantics, type discrimination
(refresh tokens can't sneak past the access decoder, and vice versa),
and the public `/auth/refresh` endpoint.
"""

from __future__ import annotations

import time

import jwt
import pytest
from fastapi.testclient import TestClient

from agora.interfaces.api.main import create_app
from agora.interfaces.api.routers import match as match_router
from agora.interfaces.api.security import (
    AuthenticatedUser,
    decode_access_token,
    decode_refresh_token,
    issue_access_token,
    issue_refresh_token,
    refresh_blacklist,
)
from agora.interfaces.api.settings import get_settings


@pytest.fixture(autouse=True)
def _reset_blacklist() -> None:
    refresh_blacklist.reset()


@pytest.fixture
def user() -> AuthenticatedUser:
    return AuthenticatedUser(sub="google:42", email="alice@example.com", name="Alice")


@pytest.fixture
def client() -> TestClient:
    match_router._runtime = None
    return TestClient(create_app())


# ──────────────────────────────────────────────────────────────────────────
# Token issuance shape
# ──────────────────────────────────────────────────────────────────────────


def test_access_token_carries_typ_access(user: AuthenticatedUser) -> None:
    settings = get_settings()
    token = issue_access_token(user)
    payload = jwt.decode(
        token,
        settings.jwt_signing_secret,
        algorithms=["HS256"],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
    )
    assert payload["typ"] == "access"
    assert payload["sub"] == "google:42"
    assert "jti" in payload


def test_refresh_token_carries_typ_refresh_and_longer_ttl(
    user: AuthenticatedUser,
) -> None:
    settings = get_settings()
    access = jwt.decode(
        issue_access_token(user),
        settings.jwt_signing_secret,
        algorithms=["HS256"],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
    )
    refresh = jwt.decode(
        issue_refresh_token(user),
        settings.jwt_signing_secret,
        algorithms=["HS256"],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
    )
    assert refresh["typ"] == "refresh"
    # Refresh outlives access by at least the configured difference.
    assert refresh["exp"] > access["exp"]
    assert refresh["jti"] != access["jti"]


# ──────────────────────────────────────────────────────────────────────────
# Type discrimination
# ──────────────────────────────────────────────────────────────────────────


def test_access_decoder_rejects_refresh_token(user: AuthenticatedUser) -> None:
    refresh = issue_refresh_token(user)
    with pytest.raises(Exception) as exc:  # HTTPException
        decode_access_token(refresh, get_settings())
    assert "Expected" in str(exc.value)


def test_refresh_decoder_rejects_access_token(user: AuthenticatedUser) -> None:
    access = issue_access_token(user)
    with pytest.raises(Exception) as exc:
        decode_refresh_token(access, get_settings())
    assert "Expected" in str(exc.value)


# ──────────────────────────────────────────────────────────────────────────
# Blacklist behaviour
# ──────────────────────────────────────────────────────────────────────────


def test_refresh_decoder_rejects_consumed_jti(user: AuthenticatedUser) -> None:
    refresh = issue_refresh_token(user)
    settings = get_settings()
    decoded_user, jti, exp = decode_refresh_token(refresh, settings)
    assert decoded_user.sub == user.sub
    refresh_blacklist.mark_consumed(jti, exp)
    with pytest.raises(Exception) as exc:
        decode_refresh_token(refresh, settings)
    assert "already used" in str(exc.value)


def test_blacklist_sweeps_expired_entries() -> None:
    """An entry whose exp is in the past should be cleaned up on next access."""
    refresh_blacklist.mark_consumed("stale-jti", exp=int(time.time()) - 60)
    # Trigger the sweep by querying any other jti.
    assert refresh_blacklist.is_consumed("anything-else") is False
    assert refresh_blacklist.is_consumed("stale-jti") is False


# ──────────────────────────────────────────────────────────────────────────
# /auth/refresh endpoint
# ──────────────────────────────────────────────────────────────────────────


def test_dev_token_endpoint_returns_both_tokens(client: TestClient) -> None:
    resp = client.post("/auth/dev-token")
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["access_token"] != body["refresh_token"]


def test_refresh_endpoint_rotates_both_tokens(client: TestClient) -> None:
    initial = client.post("/auth/dev-token").json()
    resp = client.post(
        "/auth/refresh", json={"refresh_token": initial["refresh_token"]}
    )
    assert resp.status_code == 200
    rotated = resp.json()
    # Both tokens are fresh — old refresh consumed, new pair returned.
    assert rotated["access_token"]
    assert rotated["refresh_token"]
    assert rotated["refresh_token"] != initial["refresh_token"]


def test_refresh_endpoint_rejects_replayed_refresh(client: TestClient) -> None:
    initial = client.post("/auth/dev-token").json()
    first = client.post(
        "/auth/refresh", json={"refresh_token": initial["refresh_token"]}
    )
    assert first.status_code == 200
    # Same refresh token a second time should 401 (consumed).
    second = client.post(
        "/auth/refresh", json={"refresh_token": initial["refresh_token"]}
    )
    assert second.status_code == 401


def test_refresh_endpoint_rejects_access_token_in_refresh_slot(
    client: TestClient,
) -> None:
    initial = client.post("/auth/dev-token").json()
    resp = client.post(
        "/auth/refresh", json={"refresh_token": initial["access_token"]}
    )
    assert resp.status_code == 401
