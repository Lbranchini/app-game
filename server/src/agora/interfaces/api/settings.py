"""Server configuration via environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # JWT (always required)
    jwt_signing_secret: str = "dev-only-change-me"
    jwt_audience: str = "agora-clients"
    jwt_issuer: str = "agora-server"
    jwt_access_ttl_seconds: int = 60 * 15

    # Google OAuth
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str | None = None

    # Apple OAuth
    apple_team_id: str | None = None
    apple_client_id: str | None = None
    apple_key_id: str | None = None
    apple_private_key: str | None = None  # contents of the .p8 file
    apple_redirect_uri: str | None = None

    # CORS
    web_origin: str = "http://localhost:5173"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
