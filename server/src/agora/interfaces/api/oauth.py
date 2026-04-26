"""OAuth provider integration via Authlib.

Configured lazily on first access. The OAuth client is built only when the
required env vars are present so the rest of the API runs without provider
credentials in development.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from authlib.integrations.starlette_client import OAuth

from agora.interfaces.api.settings import Settings

if TYPE_CHECKING:
    from authlib.integrations.starlette_client import StarletteOAuth2App


_GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"


class OAuthRegistry:
    """Lazy holder for Authlib clients keyed by provider name."""

    def __init__(self) -> None:
        self._oauth: OAuth | None = None

    def google(self, settings: Settings) -> "StarletteOAuth2App | None":
        if not (settings.google_client_id and settings.google_client_secret):
            return None
        oauth = self._oauth or OAuth()
        if "google" not in oauth._clients:
            oauth.register(
                name="google",
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret,
                server_metadata_url=_GOOGLE_DISCOVERY_URL,
                client_kwargs={"scope": "openid email profile"},
            )
        self._oauth = oauth
        return oauth.create_client("google")


registry = OAuthRegistry()
