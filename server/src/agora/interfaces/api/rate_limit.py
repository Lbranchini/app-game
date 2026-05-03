"""Shared rate-limiter so routers can decorate their endpoints.

Keyed by the client's remote address (uses `X-Forwarded-For` when behind a
proxy, falls back to the socket peer otherwise — slowapi handles both).
For a multi-process deploy the in-memory backend should be swapped for
Redis; today the API runs single-process so memory is enough.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

# A 60s window is a reasonable default for human-paced flows; specific
# endpoints can tighten it via their own decorator.
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])
