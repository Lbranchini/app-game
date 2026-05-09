"""Arena catalog endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from agora.application.ports import ArenaRepository
from agora.domain.arena import Arena
from agora.interfaces.api.dependencies import get_arena_repository
from agora.interfaces.api.errors import raise_api_error

router = APIRouter(prefix="/arenas", tags=["arenas"])


@router.get("", response_model=list[Arena])
def list_arenas(
    repo: Annotated[ArenaRepository, Depends(get_arena_repository)],
) -> list[Arena]:
    return list(repo.all().values())


@router.get("/{arena_id}", response_model=Arena)
def get_arena(
    arena_id: str,
    repo: Annotated[ArenaRepository, Depends(get_arena_repository)],
) -> Arena:
    try:
        return repo.get(arena_id)
    except KeyError as exc:
        raise_api_error(
            status.HTTP_404_NOT_FOUND,
            "arena.not_found",
            "arena not found",
            cause=exc,
            arena_id=arena_id,
        )
