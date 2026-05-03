"""Prometheus scrape endpoint.

The actual metric instances live in `interfaces/api/metrics.py`. This
router only owns the HTTP surface so the rest of the codebase doesn't
import a route alongside its counters.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

from agora.interfaces.api.metrics import render_latest

router = APIRouter(tags=["metrics"])


@router.get("/metrics", include_in_schema=False)
def metrics_endpoint() -> Response:
    body, content_type = render_latest()
    return Response(content=body, media_type=content_type)
