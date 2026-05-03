"""FastAPI application factory and uvicorn entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from agora.interfaces.api.routers import (
    arenas,
    auth,
    characters,
    draft,
    health,
    match,
    matchmaking,
    unlocks,
)
from agora.interfaces.api.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Agora API",
        version="0.0.3",
        description="Backend for the mythological 3v3 tactical battler.",
    )
    # Authlib uses Starlette's session to round-trip OAuth state across redirects.
    app.add_middleware(SessionMiddleware, secret_key=settings.jwt_signing_secret)
    # Tightened from `allow_headers=["*"]` to the only headers the web client
    # actually sends. The browser preflight rejects anything outside this set,
    # which is the small DoS-posture win the audit called out.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(health.router)
    app.include_router(characters.router)
    app.include_router(arenas.router)
    app.include_router(auth.router)
    app.include_router(match.router)
    app.include_router(draft.router)
    app.include_router(matchmaking.router)
    app.include_router(unlocks.router)
    return app


app = create_app()


def run() -> None:
    """Entry point for `agora-api` console script."""
    import uvicorn

    uvicorn.run("agora.interfaces.api.main:app", host="0.0.0.0", port=8000, reload=True)
