"""JWT helpers and FastAPI dependency for authenticated requests."""

from __future__ import annotations

import time
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from agora.interfaces.api.settings import Settings, get_settings


class AuthenticatedUser(BaseModel):
    sub: str          # provider subject (e.g. google:1234567)
    email: str | None = None
    name: str | None = None


def issue_access_token(user: AuthenticatedUser) -> str:
    settings = get_settings()
    now = int(time.time())
    payload = {
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "sub": user.sub,
        "iat": now,
        "exp": now + settings.jwt_access_ttl_seconds,
        "email": user.email,
        "name": user.name,
    }
    return jwt.encode(payload, settings.jwt_signing_secret, algorithm="HS256")


def decode_access_token(token: str, settings: Settings) -> AuthenticatedUser:
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
    return AuthenticatedUser(
        sub=payload["sub"],
        email=payload.get("email"),
        name=payload.get("name"),
    )


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
