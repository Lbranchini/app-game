"""Draft (ban-pick) use cases for ranked matches.

State machine, per-action validation, and assembly of final teams. The
storage backend (Redis in production, in-memory in dev/tests) is abstracted
through `DraftRepository` so the use case is portable.
"""

from __future__ import annotations

import uuid
from typing import Protocol

from agora.application.ports import ArenaRepository, CharacterRepository
from agora.domain.draft import DraftPhase, DraftState
from agora.domain.enums import Side


class DraftRepository(Protocol):
    def save(self, draft: DraftState) -> None: ...
    def get(self, draft_id: str) -> DraftState: ...
    def delete(self, draft_id: str) -> None: ...


class DraftError(Exception):
    """Raised on any draft rule violation. Caller maps to HTTP/WS error frame."""


class DraftService:
    """Encapsulates the draft state machine.

    Each public method validates → mutates state → persists → returns the new
    state. Callers receive the updated `DraftState` and decide how to push it
    to clients (WebSocket frames, polling, ...).
    """

    def __init__(
        self,
        repository: DraftRepository,
        characters: CharacterRepository,
        arenas: ArenaRepository,
    ) -> None:
        self._repo = repository
        self._characters = characters
        self._arenas = arenas

    # --------------------------------------------------------------------- #
    # Lifecycle                                                             #
    # --------------------------------------------------------------------- #

    def start(
        self,
        side_a_player_id: str,
        side_b_player_id: str,
        arena_id: str,
    ) -> DraftState:
        # Validate the arena exists.
        try:
            self._arenas.get(arena_id)
        except KeyError as exc:
            raise DraftError(f"Unknown arena: {arena_id}") from exc

        draft = DraftState(
            draft_id=str(uuid.uuid4()),
            arena_id=arena_id,
            side_a_player_id=side_a_player_id,
            side_b_player_id=side_b_player_id,
            phase=DraftPhase.BAN,
        )
        self._repo.save(draft)
        return draft

    def submit_ban(self, draft_id: str, side: Side, character_id: str) -> DraftState:
        draft = self._repo.get(draft_id)
        if draft.phase is not DraftPhase.BAN:
            raise DraftError(f"Cannot ban during phase {draft.phase}")
        if draft.bans[side] is not None:
            raise DraftError(f"Side {side.value} already banned")
        self._require_character_exists(character_id)
        draft.bans[side] = character_id

        if all(v is not None for v in draft.bans.values()):
            draft.phase = DraftPhase.PICK

        self._repo.save(draft)
        return draft

    def submit_pick(self, draft_id: str, side: Side, character_id: str) -> DraftState:
        draft = self._repo.get(draft_id)
        if draft.phase is not DraftPhase.PICK:
            raise DraftError(f"Cannot pick during phase {draft.phase}")
        if draft.current_picker is not side:
            raise DraftError(f"Not side {side.value}'s turn to pick")

        self._require_character_exists(character_id)
        if character_id in draft.bans.values():
            raise DraftError(f"{character_id} is banned")
        if any(character_id in picks for picks in draft.picks.values()):
            raise DraftError(f"{character_id} is already picked")

        draft.picks[side].append(character_id)
        draft.pick_index += 1

        if draft.picks_complete:
            draft.phase = DraftPhase.CONFIRM

        self._repo.save(draft)
        return draft

    def finalize(self, draft_id: str) -> DraftState:
        """Marks a draft DONE so the caller can hand the teams to MatchEngine."""
        draft = self._repo.get(draft_id)
        if draft.phase is not DraftPhase.CONFIRM:
            raise DraftError(f"Cannot finalize during phase {draft.phase}")
        draft.phase = DraftPhase.DONE
        self._repo.save(draft)
        return draft

    def cancel(self, draft_id: str) -> DraftState:
        draft = self._repo.get(draft_id)
        draft.phase = DraftPhase.CANCELLED
        self._repo.save(draft)
        return draft

    # --------------------------------------------------------------------- #
    # Internals                                                             #
    # --------------------------------------------------------------------- #

    def _require_character_exists(self, character_id: str) -> None:
        try:
            self._characters.get(character_id)
        except KeyError as exc:
            raise DraftError(f"Unknown character: {character_id}") from exc
