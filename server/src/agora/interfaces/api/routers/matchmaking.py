"""Matchmaking — REST + WebSocket.

`POST /matchmaking/join` (authenticated) drops the caller into the queue and
attempts a pairing. If two players are queued, both get a `match_found`
WebSocket frame with the new draft id. The frontend then opens the draft WS.

The MVP queue lives in process. Production swaps in a Redis backend with
identical semantics.
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
    PlayerRepository,
)
from agora.interfaces.api import metrics
from agora.interfaces.api.dependencies import (
    get_arena_repository,
    get_character_repository,
    get_match_history_repository,
    get_player_repository,
)
from agora.interfaces.api.match_runtime import MatchRuntime
from agora.interfaces.api.routers import match as match_router
from agora.interfaces.api.security import AuthenticatedUser, authenticate_ws_token, current_user


def _sync_queue_gauge(runtime: MatchRuntime) -> None:
    """Single source of truth for the queue-depth gauge — call after any
    join/leave/pair so the value never drifts from the actual queue."""
    metrics.matchmaking_queue_depth.set(len(runtime.matchmaking.queued_player_ids()))

router = APIRouter(prefix="/matchmaking", tags=["matchmaking"])


def _runtime(
    characters: Annotated[CharacterRepository, Depends(get_character_repository)],
    arenas: Annotated[ArenaRepository, Depends(get_arena_repository)],
    history: Annotated[MatchHistoryRepository, Depends(get_match_history_repository)],
    players: Annotated[PlayerRepository, Depends(get_player_repository)],
) -> MatchRuntime:
    return match_router._get_runtime(characters, arenas, history, players)


class QueueStatus(BaseModel):
    queued: bool
    queue_size: int


@router.post("/join", response_model=QueueStatus)
async def join(
    runtime: Annotated[MatchRuntime, Depends(_runtime)],
    user: Annotated[AuthenticatedUser, Depends(current_user)],
) -> QueueStatus:
    runtime.matchmaking.join(user.sub, display_name=user.name)
    _sync_queue_gauge(runtime)
    await _try_pair_and_notify(runtime)
    return QueueStatus(
        queued=user.sub in runtime.matchmaking.queued_player_ids(),
        queue_size=len(runtime.matchmaking.queued_player_ids()),
    )


@router.post("/leave", response_model=QueueStatus)
def leave(
    runtime: Annotated[MatchRuntime, Depends(_runtime)],
    user: Annotated[AuthenticatedUser, Depends(current_user)],
) -> QueueStatus:
    runtime.matchmaking.leave(user.sub)
    _sync_queue_gauge(runtime)
    return QueueStatus(
        queued=False,
        queue_size=len(runtime.matchmaking.queued_player_ids()),
    )


@router.websocket("/ws")
async def matchmaking_ws(
    websocket: WebSocket,
    characters: Annotated[CharacterRepository, Depends(get_character_repository)],
    arenas: Annotated[ArenaRepository, Depends(get_arena_repository)],
    history: Annotated[MatchHistoryRepository, Depends(get_match_history_repository)],
    players: Annotated[PlayerRepository, Depends(get_player_repository)],
    token: str | None = Query(default=None),
) -> None:
    """Subscribes to matchmaking notifications for the authenticated player.

    Sends `{type: "queued"}` immediately, then `{type: "match_found",
    draft_id, side}` when the player is paired.
    """
    try:
        user = authenticate_ws_token(token)
    except HTTPException as exc:
        await websocket.close(code=4401, reason=exc.detail)
        return

    runtime = match_router._get_runtime(characters, arenas, history, players)
    await websocket.accept()
    runtime.attach_matchmaking_socket(user.sub, websocket)
    runtime.matchmaking.join(user.sub, display_name=user.name)
    _sync_queue_gauge(runtime)
    await websocket.send_json({"type": "queued"})

    # Pair immediately if there's already someone waiting.
    await _try_pair_and_notify(runtime)

    try:
        while True:
            # Block for client-initiated frames (e.g. `leave`).
            frame = await websocket.receive_json()
            if frame.get("type") == "leave":
                runtime.matchmaking.leave(user.sub)
                _sync_queue_gauge(runtime)
                await websocket.send_json({"type": "left"})
                await websocket.close()
                break
    except WebSocketDisconnect:
        pass
    finally:
        runtime.detach_matchmaking_socket(user.sub)
        runtime.matchmaking.leave(user.sub)
        _sync_queue_gauge(runtime)


async def _try_pair_and_notify(runtime: MatchRuntime) -> None:
    pair = runtime.matchmaking.try_pair()
    if pair is None:
        return
    _sync_queue_gauge(runtime)  # two players just left the queue
    a, b, draft = pair
    for queued_player, side in ((a, "A"), (b, "B")):
        ws = runtime.matchmaking_socket(queued_player.player_id)
        if ws is None:
            continue
        try:
            await ws.send_json(
                {"type": "match_found", "draft_id": draft.draft_id, "side": side}
            )
        except Exception:
            runtime.detach_matchmaking_socket(queued_player.player_id)
