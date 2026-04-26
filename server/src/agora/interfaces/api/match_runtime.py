"""In-process match storage + per-match broadcast hub.

A pragmatic single-process implementation that lets one or two clients drive
a match through a WebSocket. Production deployments will replace this with
a Redis-backed match store + pub/sub for fan-out across pods.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from fastapi import WebSocket

from agora.application.engine import MatchEngine
from agora.application.ports import ArenaRepository, CharacterRepository, RandomSource
from agora.application.use_cases.draft import DraftService
from agora.domain.draft import DraftState
from agora.domain.match import Action, MatchState
from agora.infrastructure.in_memory_draft_repository import InMemoryDraftRepository
from agora.infrastructure.seeded_random import SeededRandom


@dataclass
class _MatchSession:
    state: MatchState
    engine: MatchEngine
    sockets: list[WebSocket] = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class MatchRuntime:
    """In-memory store + dispatcher.

    One instance lives on the FastAPI app. Holds active matches and the draft
    service so the WebSocket router can stay thin.
    """

    def __init__(
        self,
        characters: CharacterRepository,
        arenas: ArenaRepository,
    ) -> None:
        self._characters = characters
        self._arenas = arenas
        self._sessions: dict[str, _MatchSession] = {}
        self._draft_service = DraftService(
            repository=InMemoryDraftRepository(),
            characters=characters,
            arenas=arenas,
        )

    # --------------------------------------------------------------------- #
    # Drafts                                                                #
    # --------------------------------------------------------------------- #

    @property
    def draft_service(self) -> DraftService:
        return self._draft_service

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

        team_a = [self._characters.get(cid) for cid in draft.picks[Side.A]]
        team_b = [self._characters.get(cid) for cid in draft.picks[Side.B]]
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
        self._sessions[match_id] = _MatchSession(state=state, engine=engine)
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
        return new_state, [e.model_dump() for e in events]

    def sockets_for(self, match_id: str) -> list[WebSocket]:
        session = self._sessions.get(match_id)
        return list(session.sockets) if session else []
