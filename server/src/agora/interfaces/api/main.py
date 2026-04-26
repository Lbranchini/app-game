"""FastAPI application factory and uvicorn entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from agora.interfaces.api.routers import arenas, auth, characters, health, match
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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(characters.router)
    app.include_router(arenas.router)
    app.include_router(auth.router)
    app.include_router(match.router)
    return app


app = create_app()


def run() -> None:
    """Entry point for `agora-api` console script."""
    import uvicorn

    uvicorn.run("agora.interfaces.api.main:app", host="0.0.0.0", port=8000, reload=True)
