"""Character catalog endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from agora.application.ports import CharacterRepository
from agora.domain.character import Character
from agora.interfaces.api.dependencies import get_character_repository

router = APIRouter(prefix="/characters", tags=["characters"])


@router.get("", response_model=list[Character])
def list_characters(
    repo: Annotated[CharacterRepository, Depends(get_character_repository)],
) -> list[Character]:
    return list(repo.all().values())


@router.get("/{character_id}", response_model=Character)
def get_character(
    character_id: str,
    repo: Annotated[CharacterRepository, Depends(get_character_repository)],
) -> Character:
    try:
        return repo.get(character_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="character not found") from exc
