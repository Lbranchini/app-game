"""JSON log formatter shape contract.

The formatter is what makes server logs searchable in production. Lock
its surface in so accidental changes (renamed keys, missing extras)
fail loudly.
"""

from __future__ import annotations

import json
import logging

from agora.interfaces.api.logging_setup import JsonFormatter, configure_logging


def _format_record(message: str, extra: dict[str, object]) -> dict[str, object]:
    record = logging.LogRecord(
        name="agora.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return json.loads(JsonFormatter().format(record))


def test_formatter_emits_required_envelope_fields() -> None:
    payload = _format_record("hi", {})
    assert payload["level"] == "INFO"
    assert payload["logger"] == "agora.test"
    assert payload["message"] == "hi"
    # ISO-8601 timestamp with timezone — should round-trip via fromisoformat.
    from datetime import datetime

    datetime.fromisoformat(payload["ts"])  # type: ignore[arg-type]


def test_formatter_surfaces_extra_kwargs_as_top_level_keys() -> None:
    payload = _format_record(
        "match started",
        {"match_id": "abc", "player_id": "alice", "seed": 42},
    )
    assert payload["match_id"] == "abc"
    assert payload["player_id"] == "alice"
    assert payload["seed"] == 42


def test_formatter_includes_exc_info_when_set() -> None:
    import sys

    try:
        raise RuntimeError("boom")
    except RuntimeError:
        record = logging.LogRecord(
            name="agora.test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="something failed",
            args=(),
            exc_info=sys.exc_info(),
        )
    payload = json.loads(JsonFormatter().format(record))
    assert "exc_info" in payload
    assert "RuntimeError" in payload["exc_info"]
    assert "boom" in payload["exc_info"]


def test_configure_logging_replaces_handlers_idempotently() -> None:
    configure_logging()
    root_after_first = list(logging.getLogger().handlers)
    configure_logging()
    root_after_second = list(logging.getLogger().handlers)
    # Same number of handlers — second call must clear, not stack.
    assert len(root_after_first) == len(root_after_second) == 1
