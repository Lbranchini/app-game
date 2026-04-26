"""OAuth 2.0 sign-in routes for Google and Apple.

The actual provider hand-off uses Authlib once credentials are configured
through environment variables (see settings.py). Until those env vars are
populated, the routes return 501 so the rest of the API can run in dev.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

from agora.interfaces.api.security import (
    AuthenticatedUser,
    current_user,
    issue_access_token,
)
from agora.interfaces.api.settings import Settings, get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"


@router.get("/google/login")
def google_login(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> RedirectResponse:
    if not (settings.google_client_id and settings.google_client_secret and settings.google_redirect_uri):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET / GOOGLE_REDIRECT_URI.",
        )
    # Wiring with Authlib goes here:
    #   from authlib.integrations.starlette_client import OAuth
    #   oauth = OAuth(); oauth.register('google', ...)
    #   return await oauth.google.authorize_redirect(request, settings.google_redirect_uri)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Authlib wiring pending — see docs/03-architecture.md §9.",
    )


@router.get("/google/callback")
def google_callback(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> JSONResponse:
    # On wiring: exchange code via Authlib, verify id_token against Google's JWKS,
    # upsert the player row, then return TokenResponse.
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Authlib wiring pending — see docs/03-architecture.md §9.",
    )


@router.post("/apple/callback")
def apple_callback(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> JSONResponse:
    """Apple posts a form-encoded body (not query-string) to the callback.

    Wiring should: build the Apple client_secret JWT from the .p8 key, exchange
    the code for an id_token, verify it against Apple's JWKS, then issue our
    own access token. On the FIRST callback, parse the `user` form field for
    the user's name (Apple sends it only once).
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Apple OAuth wiring pending — see docs/03-architecture.md §9.",
    )


@router.post("/dev-token", include_in_schema=False)
def dev_token(
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    """Local-only helper: returns a JWT for a fake user so the frontend can
    develop against authenticated endpoints before real OAuth is wired up.

    Disabled if `JWT_SIGNING_SECRET` is not the default placeholder.
    """
    if settings.jwt_signing_secret != "dev-only-change-me":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user = AuthenticatedUser(sub="dev:local", email="dev@local", name="Dev User")
    return TokenResponse(access_token=issue_access_token(user))


@router.get("/me", response_model=AuthenticatedUser)
def me(user: Annotated[AuthenticatedUser, Depends(current_user)]) -> AuthenticatedUser:
    return user
