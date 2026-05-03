"""Apple Sign-In helpers: client_secret JWT + id_token verification.

Apple's OAuth dance differs from Google's in two important ways:

1.  The `client_secret` you send to the token endpoint is itself a JWT,
    signed with an ES256 private key (the `.p8` Apple downloads when you
    create a key in the developer portal).
2.  Apple posts the callback as `application/x-www-form-urlencoded` to
    your registered redirect URI; the user's name only arrives the first
    time they sign in, never again.

The `_token_exchange` helper hits Apple's token endpoint; `verify_id_token`
fetches Apple's JWKS and validates the `id_token`. Both are isolated from
the FastAPI route so they're testable in pieces.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import httpx
import jwt
from jwt import PyJWKClient

APPLE_TOKEN_URL = "https://appleid.apple.com/auth/token"
APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER = "https://appleid.apple.com"

# Apple's docs cap the lifetime of the client_secret JWT at 6 months;
# we mint a fresh short-lived one per token exchange so a leaked one
# expires fast. Five minutes is plenty for a single request round-trip.
CLIENT_SECRET_TTL_SECONDS = 300


@dataclass(frozen=True)
class AppleAuthConfig:
    team_id: str
    client_id: str
    key_id: str
    private_key_pem: str  # contents of the .p8 file


@dataclass(frozen=True)
class AppleAuthClaims:
    """Subset of the Apple id_token claims we consume."""

    sub: str
    email: str | None


def build_client_secret(config: AppleAuthConfig, *, now: int | None = None) -> str:
    """Mint the ES256-signed client_secret JWT Apple's token endpoint expects.

    Apple-specific shape:
      iss = team_id    (Apple's team identifier, NOT the client_id)
      sub = client_id  (your service id, e.g. com.example.web)
      aud = APPLE_ISSUER
    """
    issued = now if now is not None else int(time.time())
    payload = {
        "iss": config.team_id,
        "iat": issued,
        "exp": issued + CLIENT_SECRET_TTL_SECONDS,
        "aud": APPLE_ISSUER,
        "sub": config.client_id,
    }
    headers = {"kid": config.key_id, "alg": "ES256"}
    return jwt.encode(
        payload,
        config.private_key_pem,
        algorithm="ES256",
        headers=headers,
    )


@lru_cache(maxsize=1)
def _jwk_client() -> PyJWKClient:
    # PyJWKClient caches keys internally; the lru_cache here just memoises
    # the client object itself so we don't re-instantiate per request.
    return PyJWKClient(APPLE_JWKS_URL, cache_keys=True)


def verify_id_token(id_token: str, *, expected_aud: str) -> AppleAuthClaims:
    """Validate an Apple-issued id_token and return its essential claims."""
    signing_key = _jwk_client().get_signing_key_from_jwt(id_token)
    decoded: dict[str, Any] = jwt.decode(
        id_token,
        signing_key.key,
        algorithms=["RS256"],
        audience=expected_aud,
        issuer=APPLE_ISSUER,
        options={"require": ["sub", "exp", "iss", "aud"]},
    )
    sub = decoded.get("sub")
    if not isinstance(sub, str) or not sub:
        raise ValueError("Apple id_token missing `sub` claim")
    raw_email = decoded.get("email")
    email = raw_email if isinstance(raw_email, str) else None
    return AppleAuthClaims(sub=sub, email=email)


async def exchange_code_for_token(
    config: AppleAuthConfig,
    *,
    code: str,
    redirect_uri: str,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Trade an authorization code for an id_token + access_token bundle.

    Pass a custom `client` from tests to mock Apple's endpoint.
    """
    secret = build_client_secret(config)
    data = {
        "client_id": config.client_id,
        "client_secret": secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }
    owns_client = client is None
    http = client or httpx.AsyncClient(timeout=10.0)
    try:
        response = await http.post(APPLE_TOKEN_URL, data=data)
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]
    finally:
        if owns_client:
            await http.aclose()
