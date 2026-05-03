"""OAuth 2.0 sign-in routes for Google and Apple.

Google is wired through Authlib end-to-end: clicking the login button at
`/auth/google/login` redirects to Google, the callback exchanges the code,
verifies the ID token, and returns our own short-lived JWT for the rest of
the session. The provider call is skipped (501) until env vars are set.

Apple's flow is documented in `docs/03-architecture.md §9` but not yet
implemented here — its callback is form-encoded POST and it requires a
client secret JWT signed with a `.p8` key.
"""

from __future__ import annotations

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

from agora.application.ports import PlayerRepository
from agora.domain.player import Player
from agora.interfaces.api.apple_oauth import (
    AppleAuthConfig,
    exchange_code_for_token,
    verify_id_token,
)
from agora.interfaces.api.dependencies import get_player_repository
from agora.interfaces.api.oauth import registry
from agora.interfaces.api.rate_limit import limiter
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


class MeResponse(BaseModel):
    """Profile payload returned by `/auth/me`.

    `player` is `None` when the JWT subject doesn't have a row in the players
    table — e.g. the local `/auth/dev-token` flow before the dev account has
    completed any sign-in.
    """

    sub: str
    email: str | None
    name: str | None
    player: Player | None = None


@router.get("/google/login")
@limiter.limit("10/minute")
async def google_login(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> RedirectResponse:
    if not settings.google_redirect_uri:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="GOOGLE_REDIRECT_URI is not configured.",
        )
    client = registry.google(settings)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET.",
        )
    return await client.authorize_redirect(request, settings.google_redirect_uri)


@router.get("/google/callback")
@limiter.limit("10/minute")
async def google_callback(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    players: Annotated[PlayerRepository, Depends(get_player_repository)],
) -> RedirectResponse:
    client = registry.google(settings)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth not configured.",
        )
    token = await client.authorize_access_token(request)
    userinfo = token.get("userinfo")
    if userinfo is None:
        # Older Authlib returns id_token claims under a different shape.
        userinfo = await client.parse_id_token(request, token)
    if not userinfo or not userinfo.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google did not return an authenticated subject.",
        )
    provider_subject = f"google:{userinfo['sub']}"
    player = players.upsert_by_provider(
        provider_subject=provider_subject,
        email=userinfo.get("email"),
        name=userinfo.get("name"),
    )
    user = AuthenticatedUser(
        sub=provider_subject,
        email=player.email,
        name=player.name,
    )
    jwt_token = issue_access_token(user)
    frontend_url = settings.web_origin.rstrip("/")
    return RedirectResponse(
        url=f"{frontend_url}/login?token={jwt_token}", status_code=302
    )


def _apple_config_or_none(settings: Settings) -> AppleAuthConfig | None:
    parts = (
        settings.apple_team_id,
        settings.apple_client_id,
        settings.apple_key_id,
        settings.apple_private_key,
        settings.apple_redirect_uri,
    )
    if not all(parts):
        return None
    return AppleAuthConfig(
        team_id=settings.apple_team_id or "",
        client_id=settings.apple_client_id or "",
        key_id=settings.apple_key_id or "",
        private_key_pem=settings.apple_private_key or "",
    )


@router.post("/apple/callback")
@limiter.limit("10/minute")
async def apple_callback(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    players: Annotated[PlayerRepository, Depends(get_player_repository)],
) -> JSONResponse:
    """Form-encoded callback from Apple after the user grants consent.

    Apple posts `code`, `id_token` (JWT), and on the first login a JSON
    `user` blob. We exchange the code for tokens, verify the id_token
    against Apple's JWKS, then upsert the player and mint our own JWT.
    """
    config = _apple_config_or_none(settings)
    if config is None or settings.apple_redirect_uri is None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=(
                "Apple OAuth not configured. Set APPLE_TEAM_ID / APPLE_CLIENT_ID"
                " / APPLE_KEY_ID / APPLE_PRIVATE_KEY / APPLE_REDIRECT_URI."
            ),
        )

    form = await request.form()
    code = form.get("code")
    if not isinstance(code, str) or not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apple callback missing `code`.",
        )

    try:
        token_payload = await exchange_code_for_token(
            config,
            code=code,
            redirect_uri=settings.apple_redirect_uri,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Apple token exchange failed: {exc}",
        ) from exc

    id_token = token_payload.get("id_token")
    if not isinstance(id_token, str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Apple did not return an id_token.",
        )

    try:
        claims = verify_id_token(id_token, expected_aud=config.client_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Apple id_token failed verification: {exc}",
        ) from exc

    # Apple only sends `user.name` on the *first* sign-in; subsequent logins
    # have to fall back to whatever we stored. Read it best-effort so a fresh
    # sign-up gets a name on the player row.
    name: str | None = None
    raw_user = form.get("user")
    if isinstance(raw_user, str):
        import json as _json

        try:
            parsed = _json.loads(raw_user)
            user_name = parsed.get("name") if isinstance(parsed, dict) else None
            if isinstance(user_name, dict):
                first = user_name.get("firstName")
                last = user_name.get("lastName")
                joined = " ".join(p for p in (first, last) if isinstance(p, str))
                name = joined or None
        except _json.JSONDecodeError:
            name = None

    provider_subject = f"apple:{claims.sub}"
    player = players.upsert_by_provider(
        provider_subject=provider_subject,
        email=claims.email,
        name=name,
    )
    user = AuthenticatedUser(
        sub=provider_subject,
        email=player.email,
        name=player.name,
    )
    return JSONResponse(
        TokenResponse(access_token=issue_access_token(user)).model_dump()
    )


@router.post("/dev-token", include_in_schema=False)
@limiter.limit("30/minute")
def dev_token(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    """Local-only helper: issues a JWT for a fake user.

    Disabled if `JWT_SIGNING_SECRET` has been changed from its placeholder —
    that signal is enough to detect non-local environments.
    """
    if settings.jwt_signing_secret != "dev-only-change-me":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user = AuthenticatedUser(sub="dev:local", email="dev@local", name="Dev User")
    return TokenResponse(access_token=issue_access_token(user))


@router.get("/me", response_model=MeResponse)
def me(
    user: Annotated[AuthenticatedUser, Depends(current_user)],
    players: Annotated[PlayerRepository, Depends(get_player_repository)],
) -> MeResponse:
    return MeResponse(
        sub=user.sub,
        email=user.email,
        name=user.name,
        player=players.get_by_provider(user.sub),
    )
