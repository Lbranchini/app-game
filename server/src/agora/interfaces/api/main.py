"""FastAPI application factory and uvicorn entry point."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.sessions import SessionMiddleware

from agora.interfaces.api.logging_setup import configure_logging
from agora.interfaces.api.rate_limit import limiter
from agora.interfaces.api.routers import (
    arenas,
    auth,
    characters,
    draft,
    health,
    match,
    matchmaking,
    metrics as metrics_router,
    unlocks,
)
from agora.interfaces.api.settings import get_settings


class ErrorResponse(BaseModel):
    """Single, predictable shape every error response collapses to.

    Clients can pattern-match `code` (a stable machine string) and surface
    `message` to humans. `details` is free-form for validators or fields
    that need to point at a specific input.
    """

    code: str = Field(..., examples=["http_404", "validation_error", "rate_limited"])
    message: str
    details: dict[str, object] | None = None


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
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
    # Per-IP rate limiting, in-memory. Per-route limits decorate sensitive
    # endpoints (auth, dev match start) for tighter caps; the default keeps
    # ambient abuse under control.
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Unified error envelope. FastAPI's default for HTTPException returns
    # `{"detail": "..."}` which the client has to special-case. Wrap every
    # explicit HTTPException + every Pydantic ValidationError into the same
    # `ErrorResponse` shape so the client only learns one decoder.
    @app.exception_handler(HTTPException)
    async def _http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        # Routes that raise via `raise_api_error(...)` ship a structured
        # detail dict with a stable `code`; preserve it through the
        # envelope. Plain string `detail` keeps the legacy `http_<status>`
        # auto-code so clients without a localized lookup don't regress.
        if isinstance(exc.detail, dict) and "code" in exc.detail and "message" in exc.detail:
            payload = ErrorResponse(
                code=str(exc.detail["code"]),
                message=str(exc.detail["message"]),
                details=exc.detail.get("vars") if isinstance(exc.detail.get("vars"), dict) else None,
            )
        else:
            payload = ErrorResponse(
                code=f"http_{exc.status_code}",
                message=str(exc.detail) if exc.detail is not None else "",
            )
        return JSONResponse(
            status_code=exc.status_code,
            content=payload.model_dump(),
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                code="validation_error",
                message="Request payload failed validation.",
                details={"errors": exc.errors()},
            ).model_dump(),
        )

    app.include_router(health.router)
    app.include_router(characters.router)
    app.include_router(arenas.router)
    app.include_router(auth.router)
    app.include_router(match.router)
    app.include_router(draft.router)
    app.include_router(matchmaking.router)
    app.include_router(unlocks.router)
    app.include_router(metrics_router.router)
    return app


app = create_app()


def run() -> None:
    """Entry point for `agora-api` console script."""
    import uvicorn

    uvicorn.run("agora.interfaces.api.main:app", host="0.0.0.0", port=8000, reload=True)
