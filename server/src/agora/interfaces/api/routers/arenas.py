"""Arena catalog endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from agora.application.ports import ArenaRepository
from agora.domain.arena import Arena
from agora.interfaces.api.dependencies import get_arena_repository

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="arena not found") from exc
