"""Draft (ban-pick) REST endpoints.

Thin layer over `DraftService`. Errors raised by the service are translated
to 400 Bad Request — the service is the source of truth on what's a valid
move. `POST /{id}/finalize` also creates the match and returns its id so the
frontend can hop straight to the battle screen.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import BaseModel

from agora.application.ports import (
    ArenaRepository,
    CharacterRepository,
    MatchHistoryRepository,
)
from agora.application.use_cases.draft import DraftError
from agora.domain.draft import DraftPhase, DraftState
from agora.domain.enums import Side
from agora.interfaces.api.dependencies import (
    get_arena_repository,
    get_character_repository,
    get_match_history_repository,
)
from agora.interfaces.api.match_runtime import MatchRuntime
from agora.interfaces.api.routers import match as match_router
from agora.interfaces.api.security import authenticate_ws_token

router = APIRouter(prefix="/draft", tags=["draft"])


def _runtime(
    characters: Annotated[CharacterRepository, Depends(get_character_repository)],
    arenas: Annotated[ArenaRepository, Depends(get_arena_repository)],
    history: Annotated[MatchHistoryRepository, Depends(get_match_history_repository)],
) -> MatchRuntime:
    return match_router._get_runtime(characters, arenas, history)


# --------------------------------------------------------------------------- #
# Request / response models                                                   #
# --------------------------------------------------------------------------- #


class StartBody(BaseModel):
    side_a_player_id: str
    side_b_player_id: str
    arena_id: str = "neutral"


class BanPickBody(BaseModel):
    side: Side
    character_id: str


class FinalizeResponse(BaseModel):
    draft: DraftState
    match_id: str


# --------------------------------------------------------------------------- #
# Endpoints                                                                   #
# --------------------------------------------------------------------------- #


async def _broadcast(runtime: MatchRuntime, draft: DraftState, extra: dict[str, object] | None = None) -> None:
    """Send the current draft state to every subscriber. Drops dead sockets."""
    payload: dict[str, object] = {"type": "state", "draft": draft.model_dump(mode="json")}
    if extra:
        payload.update(extra)
    for ws in runtime.draft_sockets_for(draft.draft_id):
        try:
            await ws.send_json(payload)
        except Exception:  # noqa: BLE001
            runtime.detach_draft_socket(draft.draft_id, ws)


@router.post("/start", response_model=DraftState)
async def start_draft(
    body: StartBody,
    runtime: Annotated[MatchRuntime, Depends(_runtime)],
) -> DraftState:
    try:
        draft = runtime.draft_service.start(
            body.side_a_player_id, body.side_b_player_id, body.arena_id
        )
    except DraftError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await _broadcast(runtime, draft)
    return draft


@router.get("/{draft_id}", response_model=DraftState)
def get_draft(
    draft_id: str,
    runtime: Annotated[MatchRuntime, Depends(_runtime)],
) -> DraftState:
    try:
        return runtime.draft_service.get(draft_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="draft not found") from exc


@router.post("/{draft_id}/ban", response_model=DraftState)
async def submit_ban(
    draft_id: str,
    body: BanPickBody,
    runtime: Annotated[MatchRuntime, Depends(_runtime)],
) -> DraftState:
    try:
        draft = runtime.draft_service.submit_ban(draft_id, body.side, body.character_id)
    except DraftError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="draft not found") from exc
    await _broadcast(runtime, draft)
    return draft


@router.post("/{draft_id}/pick", response_model=DraftState)
async def submit_pick(
    draft_id: str,
    body: BanPickBody,
    runtime: Annotated[MatchRuntime, Depends(_runtime)],
) -> DraftState:
    try:
        draft = runtime.draft_service.submit_pick(draft_id, body.side, body.character_id)
    except DraftError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="draft not found") from exc
    await _broadcast(runtime, draft)
    return draft


@router.post("/{draft_id}/finalize", response_model=FinalizeResponse)
async def finalize_draft(
    draft_id: str,
    runtime: Annotated[MatchRuntime, Depends(_runtime)],
) -> FinalizeResponse:
    import uuid

    try:
        draft = runtime.draft_service.finalize(draft_id)
    except DraftError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="draft not found") from exc

    if draft.phase is not DraftPhase.DONE:
        raise HTTPException(status_code=400, detail=f"draft phase is {draft.phase}")

    match_id = str(uuid.uuid4())
    runtime.create_match_from_draft(draft, match_id=match_id, seed=0)
    await _broadcast(runtime, draft, {"match_id": match_id})
    return FinalizeResponse(draft=draft, match_id=match_id)


@router.post("/{draft_id}/cancel", response_model=DraftState)
async def cancel_draft(
    draft_id: str,
    runtime: Annotated[MatchRuntime, Depends(_runtime)],
) -> DraftState:
    try:
        draft = runtime.draft_service.cancel(draft_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="draft not found") from exc
    await _broadcast(runtime, draft)
    return draft


@router.websocket("/ws/{draft_id}")
async def draft_ws(
    websocket: WebSocket,
    draft_id: str,
    characters: Annotated[CharacterRepository, Depends(get_character_repository)],
    arenas: Annotated[ArenaRepository, Depends(get_arena_repository)],
    history: Annotated[MatchHistoryRepository, Depends(get_match_history_repository)],
    token: str | None = Query(default=None),
) -> None:
    """Subscribe to draft state changes.

    Validates the JWT, ensures the user is one of the two participants, then
    pushes the current state immediately and every subsequent change.
    """
    try:
        user = authenticate_ws_token(token)
    except HTTPException as exc:
        await websocket.close(code=4401, reason=exc.detail)
        return

    runtime = match_router._get_runtime(characters, arenas, history)
    try:
        draft = runtime.draft_service.get(draft_id)
    except KeyError:
        await websocket.close(code=4404)
        return
    if user.sub not in (draft.side_a_player_id, draft.side_b_player_id):
        await websocket.close(code=4403, reason="not a participant")
        return

    await websocket.accept()
    runtime.attach_draft_socket(draft_id, websocket)
    await websocket.send_json({"type": "state", "draft": draft.model_dump(mode="json")})

    try:
        while True:
            # Subscribers don't speak — drop anything they send. Any client
            # close exits the loop via WebSocketDisconnect.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        runtime.detach_draft_socket(draft_id, websocket)
