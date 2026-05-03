"""Structured JSON logging for the API.

The Python stdlib logging is fine for what we need; we just swap the
text formatter for a JSON one so the output ships cleanly into ELK,
Datadog, Loki, etc.

Usage from any module:

    import logging
    log = logging.getLogger(__name__)
    log.info("match started", extra={"match_id": m.id, "player_id": p.id})

The `extra` keys come through as top-level JSON fields. The formatter
also flattens common contextual fields (match_id, player_id, request_id)
when present so log searches don't have to grep into nested dicts.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

# Stdlib LogRecord attributes are well-known; anything not in this list is
# treated as user-supplied context and serialized as a top-level field.
_RESERVED_FIELDS = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    }
)


class JsonFormatter(logging.Formatter):
    """Single-line JSON output, one log event per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        # Anything the caller passed through `extra={}` lands as a non-reserved
        # attribute on the record. Surface them as top-level JSON fields.
        for key, value in record.__dict__.items():
            if key in _RESERVED_FIELDS or key.startswith("_"):
                continue
            payload[key] = value
        return json.dumps(payload, default=str, separators=(",", ":"))


def configure_logging(level: int = logging.INFO) -> None:
    """Idempotently install the JSON formatter on the root logger."""
    root = logging.getLogger()
    # Remove any prior handlers so re-running `create_app()` (in tests) doesn't
    # stack duplicates.
    for h in list(root.handlers):
        root.removeHandler(h)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level)
    # Quiet down access logs we don't author; keep the formatter consistent.
    logging.getLogger("uvicorn.access").handlers = [handler]
    logging.getLogger("uvicorn.error").handlers = [handler]
