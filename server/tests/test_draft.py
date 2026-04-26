"""Tests for the draft (ban-pick) state machine."""

from __future__ import annotations

import pytest

from agora.application.ports import ArenaRepository, CharacterRepository
from agora.application.use_cases.draft import DraftError, DraftService
from agora.domain.draft import DraftPhase
from agora.domain.enums import Side
from agora.infrastructure.in_memory_draft_repository import InMemoryDraftRepository
from agora.infrastructure.yaml_arena_repository import YamlArenaRepository


@pytest.fixture
def arena_repo() -> ArenaRepository:
    return YamlArenaRepository()


@pytest.fixture
def service(repository: CharacterRepository, arena_repo: ArenaRepository) -> DraftService:
    return DraftService(
        repository=InMemoryDraftRepository(),
        characters=repository,
        arenas=arena_repo,
    )


def test_full_happy_path_snake_pick_order(service: DraftService) -> None:
    draft = service.start("p1", "p2", arena_id="olympus")
    assert draft.phase is DraftPhase.BAN
    assert draft.pick_order == [Side.A, Side.B, Side.B, Side.A, Side.A, Side.B]

    service.submit_ban(draft.draft_id, Side.A, "loki")
    draft = service.submit_ban(draft.draft_id, Side.B, "anubis")
    assert draft.phase is DraftPhase.PICK

    # Snake order: A, B, B, A, A, B.
    service.submit_pick(draft.draft_id, Side.A, "achilles")
    service.submit_pick(draft.draft_id, Side.B, "thor")
    service.submit_pick(draft.draft_id, Side.B, "isis")
    service.submit_pick(draft.draft_id, Side.A, "athena")
    service.submit_pick(draft.draft_id, Side.A, "medusa")
    draft = service.submit_pick(draft.draft_id, Side.B, "amaterasu")

    assert draft.phase is DraftPhase.CONFIRM
    assert draft.picks[Side.A] == ["achilles", "athena", "medusa"]
    assert draft.picks[Side.B] == ["thor", "isis", "amaterasu"]

    final = service.finalize(draft.draft_id)
    assert final.phase is DraftPhase.DONE


def test_unknown_arena_rejected(service: DraftService) -> None:
    with pytest.raises(DraftError):
        service.start("p1", "p2", arena_id="atlantis")


def test_cannot_ban_outside_ban_phase(service: DraftService) -> None:
    draft = service.start("p1", "p2", "neutral")
    service.submit_ban(draft.draft_id, Side.A, "loki")
    service.submit_ban(draft.draft_id, Side.B, "anubis")  # advances to PICK
    with pytest.raises(DraftError):
        service.submit_ban(draft.draft_id, Side.A, "achilles")


def test_cannot_pick_out_of_turn(service: DraftService) -> None:
    draft = service.start("p1", "p2", "neutral")
    service.submit_ban(draft.draft_id, Side.A, "loki")
    service.submit_ban(draft.draft_id, Side.B, "anubis")
    # Snake: A's turn first.
    with pytest.raises(DraftError):
        service.submit_pick(draft.draft_id, Side.B, "thor")


def test_cannot_pick_a_banned_character(service: DraftService) -> None:
    draft = service.start("p1", "p2", "neutral")
    service.submit_ban(draft.draft_id, Side.A, "loki")
    service.submit_ban(draft.draft_id, Side.B, "anubis")
    with pytest.raises(DraftError):
        service.submit_pick(draft.draft_id, Side.A, "loki")


def test_cannot_pick_already_picked_character(service: DraftService) -> None:
    draft = service.start("p1", "p2", "neutral")
    service.submit_ban(draft.draft_id, Side.A, "loki")
    service.submit_ban(draft.draft_id, Side.B, "anubis")
    service.submit_pick(draft.draft_id, Side.A, "achilles")
    with pytest.raises(DraftError):
        service.submit_pick(draft.draft_id, Side.B, "achilles")


def test_unknown_character_rejected(service: DraftService) -> None:
    draft = service.start("p1", "p2", "neutral")
    with pytest.raises(DraftError):
        service.submit_ban(draft.draft_id, Side.A, "godzilla")


def test_double_ban_rejected(service: DraftService) -> None:
    draft = service.start("p1", "p2", "neutral")
    service.submit_ban(draft.draft_id, Side.A, "loki")
    with pytest.raises(DraftError):
        service.submit_ban(draft.draft_id, Side.A, "thor")


def test_cancel_marks_state_cancelled(service: DraftService) -> None:
    draft = service.start("p1", "p2", "neutral")
    cancelled = service.cancel(draft.draft_id)
    assert cancelled.phase is DraftPhase.CANCELLED
