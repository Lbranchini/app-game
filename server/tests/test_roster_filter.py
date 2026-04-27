"""Tests for the unlocked-roster filter on DraftService.submit_pick."""

from __future__ import annotations

import pytest

from agora.application.ports import CharacterRepository
from agora.application.use_cases.draft import DraftError, DraftService
from agora.domain.enums import Side
from agora.infrastructure.in_memory_draft_repository import InMemoryDraftRepository
from agora.infrastructure.yaml_arena_repository import YamlArenaRepository


def _service(
    repository: CharacterRepository,
    unlocked_filter: object | None = None,
) -> DraftService:
    arenas = YamlArenaRepository()
    if unlocked_filter is None:
        return DraftService(
            repository=InMemoryDraftRepository(),
            characters=repository,
            arenas=arenas,
        )
    return DraftService(
        repository=InMemoryDraftRepository(),
        characters=repository,
        arenas=arenas,
        unlocked_filter=unlocked_filter,  # type: ignore[arg-type]
    )


def test_default_filter_allows_anything(repository: CharacterRepository) -> None:
    service = _service(repository)
    draft = service.start("p1", "p2", "neutral")
    service.submit_ban(draft.draft_id, Side.A, "loki")
    service.submit_ban(draft.draft_id, Side.B, "anubis")
    # The default filter is permissive — picking succeeds.
    service.submit_pick(draft.draft_id, Side.A, "achilles")


def test_filter_rejects_locked_character(repository: CharacterRepository) -> None:
    UNLOCKED = {
        "p1": {"achilles", "athena", "thor", "anubis", "isis", "anansi", "joan_of_arc", "loki"},
        "p2": {"achilles", "athena", "thor", "anubis", "isis", "anansi", "joan_of_arc", "loki"},
    }

    def filt(player_subject: str, character_id: str) -> bool:
        return character_id in UNLOCKED.get(player_subject, set())

    service = _service(repository, unlocked_filter=filt)
    draft = service.start("p1", "p2", "neutral")
    service.submit_ban(draft.draft_id, Side.A, "medusa")
    service.submit_ban(draft.draft_id, Side.B, "cleopatra")

    # `mulan` is NOT in either player's unlocked set above.
    with pytest.raises(DraftError) as exc_info:
        service.submit_pick(draft.draft_id, Side.A, "mulan")
    assert "unlocked roster" in str(exc_info.value)


def test_filter_uses_correct_player_for_each_side(
    repository: CharacterRepository,
) -> None:
    """A character locked for Alice but unlocked for Bob can be picked by Bob."""
    UNLOCKED = {
        "alice": {"achilles", "athena", "anubis"},
        "bob": {"achilles", "athena", "thor", "isis", "loki", "anubis"},
    }

    def filt(player_subject: str, character_id: str) -> bool:
        return character_id in UNLOCKED.get(player_subject, set())

    service = _service(repository, unlocked_filter=filt)
    draft = service.start("alice", "bob", "neutral")
    service.submit_ban(draft.draft_id, Side.A, "medusa")
    service.submit_ban(draft.draft_id, Side.B, "cleopatra")

    # Snake order kicks off with side A — Alice picks first.
    service.submit_pick(draft.draft_id, Side.A, "achilles")  # Alice has it
    service.submit_pick(draft.draft_id, Side.B, "thor")      # Bob has it
    service.submit_pick(draft.draft_id, Side.B, "isis")      # Bob has it
    # Alice doesn't have `loki` — should be rejected.
    with pytest.raises(DraftError):
        service.submit_pick(draft.draft_id, Side.A, "loki")
    # But Alice can still pick from her own pool.
    service.submit_pick(draft.draft_id, Side.A, "athena")
