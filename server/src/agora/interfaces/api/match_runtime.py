"""In-process match storage + per-match broadcast hub.

A pragmatic single-process implementation that lets one or two clients drive
a match through a WebSocket. Production deployments will replace this with
a Redis-backed match store + pub/sub for fan-out across pods.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime

from fastapi import WebSocket

from agora.application.engine import MatchEngine
from agora.application.ports import (
    ArenaRepository,
    CharacterRepository,
    MatchHistoryRepository,
    RandomSource,
)
from agora.application.use_cases.draft import DraftService
from agora.application.use_cases.matchmaking import (
    MatchmakingService,
    RandomArenaPicker,
)
from agora.domain.draft import DraftState
from agora.domain.match import Action, MatchState
from agora.domain.match_record import MatchRecord
from agora.infrastructure.in_memory_draft_repository import InMemoryDraftRepository
from agora.infrastructure.seeded_random import SeededRandom


@dataclass
class _MatchSession:
    state: MatchState
    engine: MatchEngine
    seed: int
    side_a_player_id: str
    side_b_player_id: str
    team_a: list[str]
    team_b: list[str]
    started_at: datetime
    sockets: list[WebSocket] = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    persisted: bool = False


class MatchRuntime:
    """In-memory store + dispatcher.

    One instance lives on the FastAPI app. Holds active matches and the draft
    service so the WebSocket router can stay thin.
    """

    def __init__(
        self,
        characters: CharacterRepository,
        arenas: ArenaRepository,
        history: MatchHistoryRepository | None = None,
    ) -> None:
        self._characters = characters
        self._arenas = arenas
        self._sessions: dict[str, _MatchSession] = {}
        self._history = history
        self._draft_service = DraftService(
            repository=InMemoryDraftRepository(),
            characters=characters,
            arenas=arenas,
        )
        self._matchmaking = MatchmakingService(
            draft_service=self._draft_service,
            arena_picker=RandomArenaPicker(list(arenas.all().keys())),
        )
        # Per-draft socket fan-out so two clients can watch one draft live.
        self._draft_sockets: dict[str, list[WebSocket]] = {}
        # Per-player matchmaking sockets so we can push `match_found`.
        self._mm_sockets: dict[str, WebSocket] = {}

    # --------------------------------------------------------------------- #
    # Drafts                                                                #
    # --------------------------------------------------------------------- #

    @property
    def draft_service(self) -> DraftService:
        return self._draft_service

    @property
    def matchmaking(self) -> MatchmakingService:
        return self._matchmaking

    def attach_draft_socket(self, draft_id: str, ws: WebSocket) -> None:
        self._draft_sockets.setdefault(draft_id, []).append(ws)

    def detach_draft_socket(self, draft_id: str, ws: WebSocket) -> None:
        sockets = self._draft_sockets.get(draft_id)
        if sockets and ws in sockets:
            sockets.remove(ws)

    def draft_sockets_for(self, draft_id: str) -> list[WebSocket]:
        return list(self._draft_sockets.get(draft_id, []))

    # --------------------------------------------------------------------- #
    # Matchmaking sockets                                                   #
    # --------------------------------------------------------------------- #

    def attach_matchmaking_socket(self, player_id: str, ws: WebSocket) -> None:
        # Replace any older socket for the same player (reconnect-safe).
        self._mm_sockets[player_id] = ws

    def detach_matchmaking_socket(self, player_id: str) -> None:
        self._mm_sockets.pop(player_id, None)

    def matchmaking_socket(self, player_id: str) -> WebSocket | None:
        return self._mm_sockets.get(player_id)

    # --------------------------------------------------------------------- #
    # Matches                                                               #
    # --------------------------------------------------------------------- #

    def create_match_from_draft(
        self,
        draft: DraftState,
        *,
        match_id: str,
        seed: int = 0,
        rng: RandomSource | None = None,
    ) -> MatchState:
        from agora.domain.enums import Side

        team_a_ids = list(draft.picks[Side.A])
        team_b_ids = list(draft.picks[Side.B])
        team_a = [self._characters.get(cid) for cid in team_a_ids]
        team_b = [self._characters.get(cid) for cid in team_b_ids]
        arena = self._arenas.get(draft.arena_id)
        engine = MatchEngine(
            characters=self._characters,
            rng=rng or SeededRandom(seed),
            arenas=self._arenas,
        )
        state = engine.start_match(
            match_id=match_id,
            player_a_id=draft.side_a_player_id,
            team_a=team_a,
            player_b_id=draft.side_b_player_id,
            team_b=team_b,
            seed=seed,
            arena=arena,
        )
        self._sessions[match_id] = _MatchSession(
            state=state,
            engine=engine,
            seed=seed,
            side_a_player_id=draft.side_a_player_id,
            side_b_player_id=draft.side_b_player_id,
            team_a=team_a_ids,
            team_b=team_b_ids,
            started_at=datetime.utcnow(),
        )
        return state

    def get(self, match_id: str) -> MatchState:
        if match_id not in self._sessions:
            raise KeyError(match_id)
        return self._sessions[match_id].state

    async def attach(self, match_id: str, ws: WebSocket) -> None:
        session = self._sessions.get(match_id)
        if session is None:
            raise KeyError(match_id)
        session.sockets.append(ws)

    def detach(self, match_id: str, ws: WebSocket) -> None:
        session = self._sessions.get(match_id)
        if session is None:
            return
        if ws in session.sockets:
            session.sockets.remove(ws)

    async def submit_actions(
        self, match_id: str, actions: list[Action]
    ) -> tuple[MatchState, list[dict[str, object]]]:
        session = self._sessions.get(match_id)
        if session is None:
            raise KeyError(match_id)
        async with session.lock:
            new_state, events = session.engine.resolve_turn(session.state, actions)
            session.state = new_state
            self._maybe_persist(match_id, session)
        return new_state, [e.model_dump() for e in events]

    def _maybe_persist(self, match_id: str, session: _MatchSession) -> None:
        """Save a `MatchRecord` exactly once when the match flips to finished."""
        if not session.state.finished or session.persisted or self._history is None:
            return
        record = MatchRecord(
            id=match_id,
            arena_id=session.state.arena_id,
            side_a_player_id=session.side_a_player_id,
            side_b_player_id=session.side_b_player_id,
            team_a=session.team_a,
            team_b=session.team_b,
            winner=session.state.winner.value if session.state.winner else None,
            turns=session.state.turn,
            seed=session.seed,
            started_at=session.started_at,
            ended_at=datetime.utcnow(),
        )
        self._history.save(record)
        session.persisted = True

    def sockets_for(self, match_id: str) -> list[WebSocket]:
        session = self._sessions.get(match_id)
        return list(session.sockets) if session else []
