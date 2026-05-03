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

# How long a participant has to reconnect before they forfeit the match.
# Skipped entirely for dev matches (synthetic player ids).
DISCONNECT_GRACE = timedelta(seconds=30)

# How often the server pushes a `{"type": "heartbeat"}` frame to each socket
# attached to a match. Failed sends drop the socket immediately, which kicks
# off the disconnect/forfeit pipeline — without this we'd only notice a dead
# connection when the OS-level TCP timeout fires (default ~2h on Linux).
HEARTBEAT_INTERVAL_SECONDS = 15.0


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
    # `sockets` pairs each connected websocket with the player_id that owns
    # it, so we can tell when the *last* socket for a player closes (vs. a
    # spectator/refresh) and decide whether to start the forfeit grace.
    sockets: list[tuple[str, WebSocket]] = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    persisted: bool = False
    # Full per-match event log so the post-match telemetry has the whole
    # game to summarize, not just the events from the final turn.
    event_log: list[Event] = field(default_factory=list)
    # Background task that fires when the active turn's deadline expires.
    deadline_task: asyncio.Task[None] | None = None
    # Player-id → instant the player went fully offline. Cleared when any
    # of their sockets re-attaches.
    disconnected_since: dict[str, datetime] = field(default_factory=dict)
    # Per-player forfeit watchers. Cancelled on reconnect.
    forfeit_tasks: dict[str, asyncio.Task[None]] = field(default_factory=dict)
    # One heartbeat loop per match; armed when first socket attaches, torn
    # down when no sockets remain or the match finishes.
    heartbeat_task: asyncio.Task[None] | None = None


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
        logger.info(
            "match started",
            extra={
                "event": "match_started",
                "match_id": match_id,
                "arena_id": state.arena_id,
                "side_a_player_id": draft.side_a_player_id,
                "side_b_player_id": draft.side_b_player_id,
                "seed": seed,
            },
        )
        return state

    def get(self, match_id: str) -> MatchState:
        if match_id not in self._sessions:
            raise KeyError(match_id)
        return self._sessions[match_id].state

    async def attach(self, match_id: str, ws: WebSocket, player_id: str | None = None) -> None:
        """Register a websocket for a match.

        `player_id` is required for real matches so disconnect tracking can
        scope correctly. Dev matches pass None and skip forfeit handling.
        """
        session = self._sessions.get(match_id)
        if session is None:
            raise KeyError(match_id)
        # Default to the side label so dev matches still get a non-empty key
        # without entangling them with the forfeit logic below.
        owner = player_id or "_anon"
        session.sockets.append((owner, ws))
        # If this player was on the forfeit clock, cancel and broadcast.
        if player_id is not None and player_id in session.disconnected_since:
            session.disconnected_since.pop(player_id, None)
            task = session.forfeit_tasks.pop(player_id, None)
            if task and not task.done():
                task.cancel()
            await self._broadcast_presence(match_id, player_id, "reconnected")
        # First attach lazily arms the deadline watcher + the heartbeat loop.
        await self._ensure_deadline_watcher(match_id)
        self._ensure_heartbeat(match_id)

    async def detach(self, match_id: str, ws: WebSocket) -> None:
        session = self._sessions.get(match_id)
        if session is None:
            return
        # Find the (owner, ws) pair and remove it.
        owner: str | None = None
        for entry in list(session.sockets):
            if entry[1] is ws:
                owner = entry[0]
                session.sockets.remove(entry)
                break
        if owner is None or owner == "_anon":
            return
        # If this player still has another live socket open, no grace yet.
        if any(o == owner for o, _ in session.sockets):
            return
        # Don't start a forfeit clock for a finished match.
        if session.state.finished:
            return
        # Last socket for this player went away — start the grace timer.
        deadline = datetime.utcnow() + DISCONNECT_GRACE
        session.disconnected_since[owner] = datetime.utcnow()
        task = asyncio.create_task(self._watch_forfeit(match_id, owner, deadline))
        session.forfeit_tasks[owner] = task
        await self._broadcast_presence(match_id, owner, "disconnected", deadline=deadline)

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
                await self.detach(match_id, ws)

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

    def _ensure_heartbeat(self, match_id: str) -> None:
        session = self._sessions.get(match_id)
        if session is None:
            return
        if session.heartbeat_task and not session.heartbeat_task.done():
            return  # already running
        session.heartbeat_task = asyncio.create_task(self._heartbeat_loop(match_id))

    async def _heartbeat_loop(self, match_id: str) -> None:
        """Push application-level pings until the match ends.

        Each tick we broadcast a `heartbeat` frame; failed sends are detached
        through the existing broadcast path, which then runs the disconnect
        pipeline (forfeit grace, presence frame to the surviving side).
        """
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
                session = self._sessions.get(match_id)
                if session is None:
                    return
                if session.state.finished:
                    return
                if not session.sockets:
                    # Nobody connected; let the loop end. attach() will rearm.
                    session.heartbeat_task = None
                    return
                payload: dict[str, object] = {
                    "type": "heartbeat",
                    "ts": datetime.utcnow().isoformat(),
                }
                for ws in self.sockets_for(match_id):
                    try:
                        await ws.send_json(payload)
                    except Exception:
                        # send_json failed → socket is dead; same recovery
                        # path as a normal disconnect.
                        await self.detach(match_id, ws)
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
                logger.info(
                    "turn auto-resolved (deadline expired)",
                    extra={
                        "event": "turn_auto_resolved",
                        "match_id": match_id,
                        "turn": session.state.turn,
                        "side": session.state.current_side.value,
                    },
                )
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

    # ------------------------------------------------------------------ #
    # Disconnect / forfeit                                               #
    # ------------------------------------------------------------------ #

    async def _watch_forfeit(self, match_id: str, player_id: str, deadline: datetime) -> None:
        """Sleep until `deadline`, then forfeit `player_id` if still offline."""
        try:
            wait = (deadline - datetime.utcnow()).total_seconds()
            if wait > 0:
                await asyncio.sleep(wait)
            await self._forfeit_if_still_disconnected(match_id, player_id, deadline)
        except asyncio.CancelledError:
            return

    async def _forfeit_if_still_disconnected(
        self, match_id: str, player_id: str, expected_since: datetime
    ) -> None:
        session = self._sessions.get(match_id)
        if session is None:
            return
        try:
            new_state: MatchState | None = None
            async with session.lock:
                if session.state.finished:
                    return
                # Reconnected during the wait — `disconnected_since` was cleared.
                still_off = session.disconnected_since.get(player_id)
                if still_off is None or still_off > expected_since:
                    return
                # Forfeit: the *other* side wins.
                from agora.domain.enums import Side

                winner = (
                    Side.B if player_id == session.side_a_player_id else Side.A
                )
                logger.info(
                    "match forfeited",
                    extra={
                        "event": "match_forfeited",
                        "match_id": match_id,
                        "player_id": player_id,
                        "winner": winner.value,
                    },
                )
                session.state.finished = True
                session.state.winner = winner
                session.state.turn_deadline = None
                # Cancel any pending deadline watcher; the match is over.
                if session.deadline_task and not session.deadline_task.done():
                    session.deadline_task.cancel()
                    session.deadline_task = None
                # Synthetic event so the post-match summary can flag this.
                forfeit_event = Event(
                    kind="forfeit",
                    details={"player_id": player_id, "winner": winner.value},
                )
                session.event_log.append(forfeit_event)
                self._maybe_persist(match_id, session)
                new_state = session.state
            if new_state is not None:
                winner_value = new_state.winner.value if new_state.winner else None
                forfeit_payload = {
                    "kind": "forfeit",
                    "details": {"player_id": player_id, "winner": winner_value},
                }
                await self._broadcast(match_id, new_state, [forfeit_payload])
        except Exception:
            logger.exception("forfeit failed for match %s", match_id)

    async def _broadcast_presence(
        self,
        match_id: str,
        player_id: str,
        kind: str,  # "disconnected" | "reconnected"
        *,
        deadline: datetime | None = None,
    ) -> None:
        payload: dict[str, object] = {
            "type": "presence",
            "player_id": player_id,
            "status": kind,
        }
        if deadline is not None:
            payload["forfeit_deadline"] = deadline.isoformat()
        for ws in self.sockets_for(match_id):
            try:
                await ws.send_json(payload)
            except Exception:
                continue

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
        logger.info(
            "match finished",
            extra={
                "event": "match_finished",
                "match_id": match_id,
                "winner": winner,
                "turns": session.state.turn,
                "elo_delta_a": delta_a,
                "elo_delta_b": delta_b,
                "side_a_player_id": session.side_a_player_id,
                "side_b_player_id": session.side_b_player_id,
            },
        )
        # Match is over — tear down the heartbeat loop too. The deadline
        # watcher already self-cancels via state.finished, but the heartbeat
        # is keyed off "any socket attached" so we have to stop it here.
        if session.heartbeat_task and not session.heartbeat_task.done():
            session.heartbeat_task.cancel()
            session.heartbeat_task = None

    def sockets_for(self, match_id: str) -> list[WebSocket]:
        session = self._sessions.get(match_id)
        if session is None:
            return []
        return [ws for _, ws in session.sockets]

    # --------------------------------------------------------------------- #
    # Lookup helpers used by route auth                                     #
    # --------------------------------------------------------------------- #

    def participants_of(self, match_id: str) -> tuple[str, str] | None:
        session = self._sessions.get(match_id)
        if session is None:
            return None
        return session.side_a_player_id, session.side_b_player_id
