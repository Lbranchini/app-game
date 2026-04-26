"""Match REST + WebSocket endpoints.

The WebSocket flow is intentionally minimal: clients connect to
`/match/ws/{match_id}`, receive state snapshots after each turn, and submit
actions via `{"type": "actions", "actions": [...]}` frames.

For dev convenience, `POST /match/dev/start` skips draft and starts a match
from two character-id lists. Production flow goes through `/draft/...` first.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel

from agora.application.ports import ArenaRepository, CharacterRepository
from agora.domain.draft import DraftPhase, DraftState
from agora.domain.enums import Side
from agora.domain.match import Action, MatchState
from agora.interfaces.api.dependencies import get_arena_repository, get_character_repository
from agora.interfaces.api.match_runtime import MatchRuntime

router = APIRouter(prefix="/match", tags=["match"])

_runtime: MatchRuntime | None = None


def _get_runtime(
    characters: Annotated[CharacterRepository, Depends(get_character_repository)],
    arenas: Annotated[ArenaRepository, Depends(get_arena_repository)],
) -> MatchRuntime:
    global _runtime
    if _runtime is None:
        _runtime = MatchRuntime(characters=characters, arenas=arenas)
    return _runtime


class DevStartBody(BaseModel):
    team_a: list[str]
    team_b: list[str]
    arena_id: str = "neutral"
    seed: int = 0


class StartedMatch(BaseModel):
    match_id: str
    state: MatchState


@router.post("/dev/start", response_model=StartedMatch)
def dev_start(
    body: DevStartBody,
    runtime: Annotated[MatchRuntime, Depends(_get_runtime)],
) -> StartedMatch:
    """Bypass draft and create a match directly. Useful for frontend dev."""
    if len(body.team_a) != 3 or len(body.team_b) != 3:
        raise HTTPException(status_code=400, detail="Each team must have 3 characters")

    fake_draft = DraftState(
        draft_id="dev",
        arena_id=body.arena_id,
        side_a_player_id="dev_a",
        side_b_player_id="dev_b",
        phase=DraftPhase.DONE,
        picks={Side.A: list(body.team_a), Side.B: list(body.team_b)},
    )
    match_id = str(uuid.uuid4())
    try:
        state = runtime.create_match_from_draft(
            fake_draft, match_id=match_id, seed=body.seed
        )
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Unknown id: {exc}") from exc
    return StartedMatch(match_id=match_id, state=state)


@router.get("/{match_id}", response_model=MatchState)
def get_match(
    match_id: str,
    runtime: Annotated[MatchRuntime, Depends(_get_runtime)],
) -> MatchState:
    try:
        return runtime.get(match_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="match not found") from exc


@router.websocket("/ws/{match_id}")
async def match_ws(
    websocket: WebSocket,
    match_id: str,
    characters: Annotated[CharacterRepository, Depends(get_character_repository)],
    arenas: Annotated[ArenaRepository, Depends(get_arena_repository)],
) -> None:
    runtime = _get_runtime(characters, arenas)

    try:
        runtime.get(match_id)  # Validate existence before accepting.
    except KeyError:
        await websocket.close(code=4404)
        return

    await websocket.accept()
    await runtime.attach(match_id, websocket)
    state = runtime.get(match_id)
    await websocket.send_json({"type": "state", "state": state.model_dump(mode="json")})

    try:
        while True:
            frame = await websocket.receive_json()
            if frame.get("type") != "actions":
                await websocket.send_json({"type": "error", "detail": "unknown frame type"})
                continue
            try:
                actions = [Action.model_validate(a) for a in frame.get("actions", [])]
            except Exception as exc:  # noqa: BLE001 — validation surfaces as ws error
                await websocket.send_json({"type": "error", "detail": f"bad action: {exc}"})
                continue

            new_state, events = await runtime.submit_actions(match_id, actions)
            payload = {
                "type": "state",
                "state": new_state.model_dump(mode="json"),
                "events": events,
            }
            for ws in runtime.sockets_for(match_id):
                try:
                    await ws.send_json(payload)
                except Exception:  # noqa: BLE001
                    runtime.detach(match_id, ws)
    except WebSocketDisconnect:
        runtime.detach(match_id, websocket)
    except Exception:  # noqa: BLE001
        runtime.detach(match_id, websocket)
        raise
