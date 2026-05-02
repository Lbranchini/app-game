"""In-process match storage + per-match broadcast hub.

A pragmatic single-process implementation that lets one or two clients drive
a match through a WebSocket. Production deployments will replace this with
a Redis-backed match store + pub/sub for fan-out across pods.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from fastapi import WebSocket

from agora.application.engine import MatchEngine
from agora.application.ports import (
    ArenaRepository,
    CharacterRepository,
    MatchHistoryRepository,
    PlayerRepository,
    RandomSource,
)
from agora.application.use_cases.draft import DraftService
from agora.application.use_cases.match_summary import summarize_events
from agora.application.use_cases.matchmaking import (
    MatchmakingService,
    RandomArenaPicker,
)
from agora.application.use_cases.missions import MissionService
from agora.application.use_cases.unlocks import UnlockService
from agora.domain.draft import DraftState
from agora.domain.events import Event
from agora.domain.match import Action, MatchState
from agora.domain.match_record import MatchRecord
from agora.domain.ratings import compute_new_ratings
from agora.infrastructure.in_memory_draft_repository import InMemoryDraftRepository
from agora.infrastructure.seeded_random import SeededRandom

logger = logging.getLogger(__name__)

# Server-authoritative turn deadline. Clients show a countdown derived from
# `state.turn_deadline`; if the deadline passes, the runtime resolves the
# turn with whatever (potentially empty) action set is queued.
TURN_DURATION = timedelta(seconds=60)


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
    # Full per-match event log so the post-match telemetry has the whole
    # game to summarize, not just the events from the final turn.
    event_log: list[Event] = field(default_factory=list)
    # Background task that fires when the active turn's deadline expires.
    deadline_task: asyncio.Task[None] | None = None


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
        players: PlayerRepository | None = None,
    ) -> None:
        self._characters = characters
        self._arenas = arenas
        self._sessions: dict[str, _MatchSession] = {}
        self._history = history
        self._players = players

        # Picks are validated against the picking player's unlocked roster.
        # `dev_*` player ids (used by /match/dev/start and the local Draft UI)
        # have no row in the players table, so no filter is enforced for them.
        def _unlocked_filter(player_subject: str, character_id: str) -> bool:
            if self._players is None or player_subject.startswith("dev_") or player_subject == "you" or player_subject == "opponent":
                return True
            player = self._players.get_by_provider(player_subject)
            if player is None:
                return True
            return character_id in player.unlocked_characters

        self._draft_service = DraftService(
            repository=InMemoryDraftRepository(),
            characters=characters,
            arenas=arenas,
            unlocked_filter=_unlocked_filter,
        )
        self._matchmaking = MatchmakingService(
            draft_service=self._draft_service,
            arena_picker=RandomArenaPicker(list(arenas.all().keys())),
        )
        self._missions = MissionService(players) if players is not None else None
        self._unlocks = UnlockService(players) if players is not None else None
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
        # Seed the first turn deadline. The watcher task is armed lazily on
        # the first WebSocket attach, since create_task needs a running loop
        # and `create_match_from_draft` is invoked from sync REST handlers.
        state.turn_deadline = datetime.utcnow() + TURN_DURATION
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
        # First attach lazily arms the deadline watcher.
        await self._ensure_deadline_watcher(match_id)

    def detach(self, match_id: str, ws: WebSocket) -> None:
        session = self._sessions.get(match_id)
        if session is None:
            return
        if ws in session.sockets:
            session.sockets.remove(ws)

    async def submit_actions(
        self,
        match_id: str,
        actions: list[Action],
        *,
        auto_resolved: bool = False,
    ) -> tuple[MatchState, list[dict[str, object]]]:
        """Resolve a turn, persist if final, broadcast, and re-arm the deadline.

        The auto-resolver passes `auto_resolved=True` so clients can show a
        small marker ("turn auto-resolved") on the resulting frame.
        """
        session = self._sessions.get(match_id)
        if session is None:
            raise KeyError(match_id)
        async with session.lock:
            new_state, events = session.engine.resolve_turn(session.state, actions)
            if not new_state.finished:
                new_state.turn_deadline = datetime.utcnow() + TURN_DURATION
            else:
                new_state.turn_deadline = None
            session.state = new_state
            session.event_log.extend(events)
            self._maybe_persist(match_id, session)
        # Re-arm + broadcast outside the lock so a slow socket can't stall
        # the engine itself.
        await self._ensure_deadline_watcher(match_id)
        event_dicts = [e.model_dump() for e in events]
        await self._broadcast(match_id, new_state, event_dicts, auto_resolved=auto_resolved)
        return new_state, event_dicts

    async def _broadcast(
        self,
        match_id: str,
        state: MatchState,
        events: list[dict[str, object]],
        *,
        auto_resolved: bool = False,
    ) -> None:
        payload: dict[str, object] = {
            "type": "state",
            "state": state.model_dump(mode="json"),
            "events": events,
        }
        if auto_resolved:
            payload["auto_resolved"] = True
        for ws in self.sockets_for(match_id):
            try:
                await ws.send_json(payload)
            except Exception:
                self.detach(match_id, ws)

    async def _ensure_deadline_watcher(self, match_id: str) -> None:
        session = self._sessions.get(match_id)
        if session is None:
            return
        # Cancel any previous watcher; deadline values may have shifted.
        if session.deadline_task and not session.deadline_task.done():
            session.deadline_task.cancel()
            session.deadline_task = None
        if session.state.finished or session.state.turn_deadline is None:
            return
        deadline = session.state.turn_deadline
        session.deadline_task = asyncio.create_task(
            self._watch_deadline(match_id, deadline)
        )

    async def _watch_deadline(self, match_id: str, deadline: datetime) -> None:
        try:
            wait = (deadline - datetime.utcnow()).total_seconds()
            if wait > 0:
                await asyncio.sleep(wait)
            await self._auto_resolve_if_due(match_id, deadline)
        except asyncio.CancelledError:
            return

    async def _auto_resolve_if_due(self, match_id: str, expected: datetime) -> None:
        """Resolve the turn with empty actions if the deadline still matches.

        The deadline check happens inside the session lock so a real
        submission landing in the same tick wins the race and this watcher
        becomes a no-op.
        """
        session = self._sessions.get(match_id)
        if session is None:
            return
        try:
            async with session.lock:
                if session.state.finished:
                    return
                if session.state.turn_deadline != expected:
                    return  # superseded by a real submission
                new_state, events = session.engine.resolve_turn(session.state, [])
                if not new_state.finished:
                    new_state.turn_deadline = datetime.utcnow() + TURN_DURATION
                else:
                    new_state.turn_deadline = None
                session.state = new_state
                session.event_log.extend(events)
                self._maybe_persist(match_id, session)
            await self._ensure_deadline_watcher(match_id)
            await self._broadcast(
                match_id,
                new_state,
                [e.model_dump() for e in events],
                auto_resolved=True,
            )
        except Exception:
            logger.exception("auto-resolve failed for match %s", match_id)

    def _maybe_persist(self, match_id: str, session: _MatchSession) -> None:
        """Save a `MatchRecord` and update ELO + counters + unlocks exactly once."""
        if not session.state.finished or session.persisted:
            return

        winner = session.state.winner.value if session.state.winner else None

        # ELO is computed first so the deltas can be persisted on the match record.
        delta_a: int | None = None
        delta_b: int | None = None
        if self._players is not None:
            player_a = self._players.get_by_provider(session.side_a_player_id)
            player_b = self._players.get_by_provider(session.side_b_player_id)
            if player_a is not None and player_b is not None:
                change = compute_new_ratings(player_a.elo, player_b.elo, winner)
                self._players.update_elo(player_a.id, change.new_a)
                self._players.update_elo(player_b.id, change.new_b)
                delta_a = change.delta_a
                delta_b = change.delta_b

        if self._history is not None:
            self._history.save(
                MatchRecord(
                    id=match_id,
                    arena_id=session.state.arena_id,
                    side_a_player_id=session.side_a_player_id,
                    side_b_player_id=session.side_b_player_id,
                    team_a=session.team_a,
                    team_b=session.team_b,
                    winner=winner,
                    turns=session.state.turn,
                    seed=session.seed,
                    started_at=session.started_at,
                    ended_at=datetime.utcnow(),
                    elo_delta_a=delta_a,
                    elo_delta_b=delta_b,
                )
            )

        # Mission counters — runs even if only one side has a Player row, so a
        # real player against an opponent still gets credit for the match.
        if self._missions is not None:
            summary = summarize_events(
                session.event_log,
                team_a=session.team_a,
                team_b=session.team_b,
                winner=winner,
            )
            self._missions.record_match_outcome(
                side_a_subject=session.side_a_player_id,
                side_b_subject=session.side_b_player_id,
                winner=winner,
                summary=summary,
            )

        # Unlock evaluation reads progress that was just updated above.
        if self._unlocks is not None and self._players is not None:
            for subject in (session.side_a_player_id, session.side_b_player_id):
                player = self._players.get_by_provider(subject)
                if player is not None:
                    self._unlocks.apply(player.id)

        session.persisted = True

    def sockets_for(self, match_id: str) -> list[WebSocket]:
        session = self._sessions.get(match_id)
        return list(session.sockets) if session else []

    # --------------------------------------------------------------------- #
    # Lookup helpers used by route auth                                     #
    # --------------------------------------------------------------------- #

    def participants_of(self, match_id: str) -> tuple[str, str] | None:
        session = self._sessions.get(match_id)
        if session is None:
            return None
        return session.side_a_player_id, session.side_b_player_id
