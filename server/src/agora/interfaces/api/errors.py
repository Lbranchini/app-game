"""Helper for raising HTTPExceptions that produce a localized envelope.

The default `raise HTTPException(status_code=..., detail="...")` ends up in
the generic exception handler as `{code: "http_<status>", message: detail}`
— fine, but the client has no stable machine code to localize against.

`raise_api_error` lets a route declare a stable `code` (machine string the
client looks up via `t("error.<code>")`) plus an English `message` fallback
plus optional template vars. The exception handler in `main.py` unpacks
the dict and surfaces all three through `ErrorResponse`.

    raise_api_error(404, "match.not_found", "match not found")
    raise_api_error(
        400,
        "match.bad_team_size",
        "Each team must have 3 characters",
        actual=len(team_a),
    )
"""

from __future__ import annotations

from typing import NoReturn

from fastapi import HTTPException


def raise_api_error(
    status_code: int,
    code: str,
    message: str,
    *,
    cause: BaseException | None = None,
    **vars: object,
) -> NoReturn:
    """Raise an HTTPException carrying a stable machine `code`.

    `cause` chains the original exception (`raise ... from cause`) when
    the helper is called from an `except ...:` block — a `from exc`
    clause on the call site itself would be a syntax error.
    """
    exc = HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message, "vars": vars or None},
    )
    if cause is not None:
        raise exc from cause
    raise exc
