"""JWT helpers and FastAPI dependency for authenticated requests.

We mint two kinds of tokens, both HS256-signed with `JWT_SIGNING_SECRET`:

* **access**  — short-lived (15 min by default), carries the player on
  every API call. Stateless: the server only verifies the signature.
* **refresh** — long-lived (30 days by default), used solely against
  `POST /auth/refresh` to obtain a fresh access token + a rotated
  refresh token. Each refresh JTI is single-use; we blacklist the old
  one when we issue a new pair.

The blacklist lives in-process for MVP. Production will swap in a
Redis-backed `RefreshTokenStore`.
"""

from __future__ import annotations

import time
import uuid
from typing import Annotated, Literal

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from agora.interfaces.api.settings import Settings, get_settings


TokenType = Literal["access", "refresh"]


class AuthenticatedUser(BaseModel):
    sub: str          # provider subject (e.g. google:1234567)
    email: str | None = None
    name: str | None = None


# ──────────────────────────────────────────────────────────────────────────
# Refresh token blacklist (in-memory for MVP)
# ──────────────────────────────────────────────────────────────────────────


class _InMemoryRefreshBlacklist:
    """Track consumed refresh JTIs so a stolen refresh can't be replayed.

    Entries auto-expire at the original token's `exp`, so the dict can't
    grow without bound for a healthy login pattern. We sweep stale entries
    lazily on every `is_consumed`/`mark_consumed` call.
    """

    def __init__(self) -> None:
        self._consumed: dict[str, int] = {}  # jti -> expires_at (unix seconds)

    def _sweep(self, now: int) -> None:
        if not self._consumed:
            return
        stale = [jti for jti, exp in self._consumed.items() if exp <= now]
        for jti in stale:
            self._consumed.pop(jti, None)

    def mark_consumed(self, jti: str, exp: int) -> None:
        now = int(time.time())
        self._sweep(now)
        self._consumed[jti] = exp

    def is_consumed(self, jti: str) -> bool:
        now = int(time.time())
        self._sweep(now)
        return jti in self._consumed

    def reset(self) -> None:
        self._consumed.clear()


# Module-level so issue/decode share state.
refresh_blacklist = _InMemoryRefreshBlacklist()


# ──────────────────────────────────────────────────────────────────────────
# Issuance
# ──────────────────────────────────────────────────────────────────────────


def _base_payload(
    user: AuthenticatedUser, *, typ: TokenType, ttl_seconds: int, settings: Settings
) -> dict[str, object]:
    now = int(time.time())
    return {
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "sub": user.sub,
        "iat": now,
        "exp": now + ttl_seconds,
        "jti": uuid.uuid4().hex,
        "typ": typ,
        "email": user.email,
        "name": user.name,
    }


def issue_access_token(user: AuthenticatedUser) -> str:
    settings = get_settings()
    payload = _base_payload(
        user, typ="access", ttl_seconds=settings.jwt_access_ttl_seconds, settings=settings
    )
    return jwt.encode(payload, settings.jwt_signing_secret, algorithm="HS256")


def issue_refresh_token(user: AuthenticatedUser) -> str:
    settings = get_settings()
    payload = _base_payload(
        user, typ="refresh", ttl_seconds=settings.jwt_refresh_ttl_seconds, settings=settings
    )
    return jwt.encode(payload, settings.jwt_signing_secret, algorithm="HS256")


# ──────────────────────────────────────────────────────────────────────────
# Decode
# ──────────────────────────────────────────────────────────────────────────


def _decode(token: str, *, expected_typ: TokenType, settings: Settings) -> dict[str, object]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_signing_secret,
            algorithms=["HS256"],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        ) from exc
    typ = payload.get("typ", "access")  # back-compat for tokens issued pre-refresh
    if typ != expected_typ:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Expected a {expected_typ} token, got {typ}",
        )
    return payload


def decode_access_token(token: str, settings: Settings) -> AuthenticatedUser:
    payload = _decode(token, expected_typ="access", settings=settings)
    return AuthenticatedUser(
        sub=str(payload["sub"]),
        email=payload.get("email"),  # type: ignore[arg-type]
        name=payload.get("name"),  # type: ignore[arg-type]
    )


def decode_refresh_token(token: str, settings: Settings) -> tuple[AuthenticatedUser, str, int]:
    """Validate a refresh token and consume its JTI.

    Returns the user, the JTI, and the original expiry so the caller can
    mark the JTI consumed in the blacklist after issuing replacements.
    """
    payload = _decode(token, expected_typ="refresh", settings=settings)
    jti = str(payload.get("jti", ""))
    if not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is missing `jti`.",
        )
    if refresh_blacklist.is_consumed(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token already used.",
        )
    user = AuthenticatedUser(
        sub=str(payload["sub"]),
        email=payload.get("email"),  # type: ignore[arg-type]
        name=payload.get("name"),  # type: ignore[arg-type]
    )
    return user, jti, int(payload["exp"])


# ──────────────────────────────────────────────────────────────────────────
# FastAPI dependencies
# ──────────────────────────────────────────────────────────────────────────


_bearer = HTTPBearer(auto_error=True)


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticatedUser:
    return decode_access_token(credentials.credentials, settings)


def authenticate_ws_token(token: str | None) -> AuthenticatedUser:
    """Decode a JWT supplied as a `?token=` query parameter on a WebSocket.

    Browsers can't easily set headers on a `WebSocket` upgrade, so we accept
    the token in the URL. Same JWT contract as the HTTP `Bearer` flow.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="WebSocket requires ?token=<jwt>",
        )
    return decode_access_token(token, get_settings())
