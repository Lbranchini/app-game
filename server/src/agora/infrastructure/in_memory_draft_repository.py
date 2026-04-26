"""In-memory `DraftRepository` for development and tests.

Production should swap in a Redis-backed implementation with the same shape:

    class RedisDraftRepository:
        def __init__(self, client: redis.Redis, ttl_seconds: int = 600) -> None: ...
        def save(self, draft: DraftState) -> None:
            self._client.set(f"draft:{draft.draft_id}", draft.model_dump_json(), ex=self._ttl)
        def get(self, draft_id: str) -> DraftState: ...

Putting the in-memory variant in `infrastructure/` keeps `application/` free
of any storage detail.
"""

from __future__ import annotations

from agora.domain.draft import DraftState


class InMemoryDraftRepository:
    def __init__(self) -> None:
        self._drafts: dict[str, DraftState] = {}

    def save(self, draft: DraftState) -> None:
        # Store a copy so callers mutating the returned state don't accidentally
        # mutate persisted data — production Redis backends serialize anyway.
        self._drafts[draft.draft_id] = draft.model_copy(deep=True)

    def get(self, draft_id: str) -> DraftState:
        if draft_id not in self._drafts:
            raise KeyError(draft_id)
        return self._drafts[draft_id].model_copy(deep=True)

    def delete(self, draft_id: str) -> None:
        self._drafts.pop(draft_id, None)
