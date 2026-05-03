"""`MatchEngine`: the orchestrator that drives a match through its life cycle.

Stateless w.r.t. matches. The engine is constructed with its dependencies
(repositories, RNG) and exposes two methods used by every interface
(CLI, FastAPI, WebSocket): `start_match` and `resolve_turn`.
"""

from __future__ import annotations

import copy

from agora.application.engine.arena_strategies import (
    apply_arena_match_start,
    apply_arena_turn_start,
)
from agora.application.engine.context import EffectContext, StatusTickContext
from agora.application.engine.effect_handlers import EFFECT_HANDLERS
from agora.application.engine.skill_validator import (
    PaymentPlan,
    ValidationFailure,
    check_can_act,
    check_cooldown,
    validate_payment,
)
from agora.application.engine.status_predicates import is_stealthed
from agora.application.engine.status_ticks import STATUS_TICK_HANDLERS
from agora.application.ports import ArenaRepository, CharacterRepository, RandomSource
from agora.domain.arena import Arena
from agora.domain.character import Character, Effect, Skill
from agora.domain.enums import (
    Essence,
    ROLLABLE_ESSENCES,
    Side,
    SkillKind,
    TargetKind,
)
from agora.domain.events import Event
from agora.domain.match import (
    Action,
    ActiveStatus,
    CharacterState,
    MatchState,
    PlayerState,
)

DODGE_SKILL_ID = "dodge"
DODGE_SKILL: Skill = Skill(
    id=DODGE_SKILL_ID,
    name="Dodge",
    kind=SkillKind.INSTANT,
    cost={Essence.GENERIC: 1},
    cooldown=4,
    target=TargetKind.SELF,
    effects=[Effect(kind="invulnerable", duration=1)],
)


class MatchEngine:
    """Encapsulates match life-cycle logic.

    The engine never holds match state of its own — every call takes the
    current `MatchState` and returns a new one + the events emitted.
    """

    def __init__(
        self,
        characters: CharacterRepository,
        rng: RandomSource,
        arenas: ArenaRepository | None = None,
    ) -> None:
        self._characters = characters
        self._rng = rng
        self._arenas = arenas

    # --------------------------------------------------------------------- #
    # Public API                                                            #
    # --------------------------------------------------------------------- #

    def start_match(
        self,
        *,
        match_id: str,
        player_a_id: str,
        team_a: list[Character],
        player_b_id: str,
        team_b: list[Character],
        seed: int = 0,
        arena: Arena | None = None,
    ) -> MatchState:
        if len(team_a) != 3 or len(team_b) != 3:
            raise ValueError("Each team must have exactly 3 characters")

        state = MatchState(
            match_id=match_id,
            arena_id=arena.id if arena else "neutral",
            a=PlayerState(
                id=player_a_id,
                side=Side.A,
                characters=[self._new_character_state(c) for c in team_a],
            ),
            b=PlayerState(
                id=player_b_id,
                side=Side.B,
                characters=[self._new_character_state(c) for c in team_b],
            ),
            rng_seed=seed,
        )

        if arena is not None:
            myth_index = {c.id: c.mythology for c in team_a + team_b}
            apply_arena_match_start(arena, state, myth_index)

        self._roll_essences(state.a, 1)
        self._roll_essences(state.b, 3)
        return state

    def resolve_turn(
        self, state: MatchState, actions: list[Action]
    ) -> tuple[MatchState, list[Event]]:
        if state.finished:
            raise RuntimeError("Match already finished")

        new_state = copy.deepcopy(state)
        events: list[Event] = []
        active = new_state.player(new_state.current_side)
        opponent = new_state.opponent(new_state.current_side)

        events.append(
            Event(
                kind="turn_started",
                details={"turn": new_state.turn, "side": active.side.value},
            )
        )

        arena = self._maybe_arena(new_state)
        apply_arena_turn_start(arena, new_state)

        self._tick_statuses(active, events)
        self._tick_statuses(opponent, events)
        if self._check_end(new_state, events):
            return new_state, events

        for action in actions:
            self._execute_action(new_state, active, opponent, action, events)

        self._decrement_cooldowns(active)

        if self._check_end(new_state, events):
            return new_state, events

        new_state.turn += 1
        new_state.current_side = Side.B if new_state.current_side is Side.A else Side.A
        new_active = new_state.player(new_state.current_side)
        alive = sum(1 for c in new_active.characters if c.alive)
        self._roll_essences(new_active, alive)

        events.append(
            Event(
                kind="turn_ended",
                details={"turn": state.turn, "side": active.side.value},
            )
        )
        return new_state, events

    # --------------------------------------------------------------------- #
    # Internals                                                             #
    # --------------------------------------------------------------------- #

    def _execute_action(
        self,
        state: MatchState,
        active: PlayerState,
        opponent: PlayerState,
        action: Action,
        events: list[Event],
    ) -> None:
        actor = self._find_character(active, action.character_id)
        if actor is None or not actor.alive:
            events.append(
                Event(
                    kind="invalid_action",
                    details={"reason": "dead_or_missing", "character": action.character_id},
                )
            )
            return

        skill = self._lookup_skill(actor.id, action.skill_id)
        if skill is None:
            events.append(
                Event(
                    kind="invalid_action",
                    details={"reason": "unknown_skill", "skill": action.skill_id},
                )
            )
            return

        # Stealth: a single-target enemy skill cannot pick a stealthed enemy.
        # AOE skills auto-filter the stealthed targets out in `_resolve_targets`.
        if (
            skill.target is TargetKind.SINGLE_ENEMY
            and action.target_ids
        ):
            picked = self._find_character(opponent, action.target_ids[0])
            if picked is not None and is_stealthed(picked):
                events.append(
                    Event(
                        kind="invalid_action",
                        details={
                            "reason": "target_stealthed",
                            "skill": skill.id,
                            "target": picked.id,
                        },
                    )
                )
                return

        for check in (check_can_act(actor, skill), check_cooldown(actor, skill)):
            if isinstance(check, ValidationFailure):
                events.append(
                    Event(
                        kind="invalid_action",
                        details={"reason": check.reason, "character": actor.id, "skill": skill.id},
                    )
                )
                return

        payment = validate_payment(active, skill, action)
        if isinstance(payment, ValidationFailure):
            events.append(
                Event(
                    kind="invalid_action",
                    details={"reason": payment.reason, "skill": skill.id},
                )
            )
            return

        self._charge(active, payment)

        events.append(
            Event(
                kind="skill_used",
                details={
                    "side": active.side.value,
                    "character": actor.id,
                    "skill": skill.id,
                    "targets": list(action.target_ids),
                },
            )
        )

        for target in self._resolve_targets(skill, actor, action, active, opponent):
            target_owner = self._owner_of(state, target)
            for effect in skill.effects:
                handler = EFFECT_HANDLERS.get(effect.kind)
                if handler is None:
                    continue
                ctx = EffectContext(
                    state=state,
                    source=actor,
                    target=target,
                    target_owner=target_owner,
                    rng=self._rng,
                    events=events,
                )
                handler.apply(effect, ctx)

        if skill.cooldown > 0:
            actor.cooldowns[skill.id] = skill.cooldown

        # Stealth breaks the moment its bearer commits an offensive action.
        # Keeps the rule symmetric: defensive/utility skills (self/ally) leave
        # stealth intact, so a stealthed character can buff allies and stay
        # hidden the same turn.
        if skill.target in (TargetKind.SINGLE_ENEMY, TargetKind.ALL_ENEMIES):
            stealth = next((s for s in actor.statuses if s.name == "stealth"), None)
            if stealth is not None:
                actor.statuses.remove(stealth)
                events.append(
                    Event(
                        kind="status_expired",
                        details={
                            "character": actor.id,
                            "status": "stealth",
                            "consumed": True,
                        },
                    )
                )

    def _tick_statuses(self, player: PlayerState, events: list[Event]) -> None:
        for character in player.characters:
            if not character.alive:
                continue
            for status in character.statuses:
                handler = STATUS_TICK_HANDLERS.get(status.name)
                if handler is not None:
                    handler.tick(
                        StatusTickContext(
                            status=status,
                            character=character,
                            player=player,
                            rng=self._rng,
                            events=events,
                        )
                    )

            if not character.alive:
                events.append(
                    Event(kind="character_defeated", details={"character": character.id})
                )

            survivors: list[ActiveStatus] = []
            for status in character.statuses:
                status.duration -= 1
                if status.duration > 0:
                    survivors.append(status)
                else:
                    events.append(
                        Event(
                            kind="status_expired",
                            details={"character": character.id, "status": status.name},
                        )
                    )
            character.statuses = survivors

    def _resolve_targets(
        self,
        skill: Skill,
        actor: CharacterState,
        action: Action,
        active: PlayerState,
        opponent: PlayerState,
    ) -> list[CharacterState]:
        if skill.target is TargetKind.SELF:
            return [actor]
        if skill.target is TargetKind.ALL_ENEMIES:
            # Stealth shields against being targeted at all — including AoE.
            return [c for c in opponent.characters if c.alive and not is_stealthed(c)]
        if skill.target is TargetKind.ALL_ALLIES:
            return [c for c in active.characters if c.alive]
        if skill.target is TargetKind.SINGLE_ENEMY:
            if not action.target_ids:
                return []
            target = self._find_character(opponent, action.target_ids[0])
            return [target] if target and target.alive else []
        if skill.target is TargetKind.SINGLE_ALLY:
            if not action.target_ids:
                return []
            target = self._find_character(active, action.target_ids[0])
            return [target] if target and target.alive else []
        return []

    def _lookup_skill(self, character_id: str, skill_id: str) -> Skill | None:
        if skill_id == DODGE_SKILL_ID:
            return DODGE_SKILL
        try:
            character = self._characters.get(character_id)
        except KeyError:
            return None
        return next((s for s in character.skills if s.id == skill_id), None)

    def _maybe_arena(self, state: MatchState) -> Arena | None:
        if self._arenas is None or state.arena_id == "neutral":
            return None
        try:
            return self._arenas.get(state.arena_id)
        except KeyError:
            return None

    def _decrement_cooldowns(self, player: PlayerState) -> None:
        for character in player.characters:
            for skill_id in list(character.cooldowns.keys()):
                character.cooldowns[skill_id] = max(0, character.cooldowns[skill_id] - 1)
                if character.cooldowns[skill_id] == 0:
                    del character.cooldowns[skill_id]

    def _roll_essences(self, player: PlayerState, count: int) -> None:
        options = [e.value for e in ROLLABLE_ESSENCES]
        for _ in range(count):
            chosen = Essence(self._rng.choice(options))
            player.essences[chosen] = player.essences.get(chosen, 0) + 1

    def _check_end(self, state: MatchState, events: list[Event]) -> bool:
        a_dead = state.a.defeated
        b_dead = state.b.defeated
        if not a_dead and not b_dead:
            return False
        state.finished = True
        if a_dead and b_dead:
            state.winner = None
            events.append(Event(kind="match_finished", details={"winner": None}))
        elif a_dead:
            state.winner = Side.B
            events.append(Event(kind="match_finished", details={"winner": "B"}))
        else:
            state.winner = Side.A
            events.append(Event(kind="match_finished", details={"winner": "A"}))
        return True

    @staticmethod
    def _new_character_state(character: Character) -> CharacterState:
        return CharacterState(
            id=character.id,
            name=character.name,
            hp=character.base_hp,
            hp_max=character.base_hp,
        )

    @staticmethod
    def _find_character(player: PlayerState, character_id: str) -> CharacterState | None:
        return next((c for c in player.characters if c.id == character_id), None)

    @staticmethod
    def _owner_of(state: MatchState, target: CharacterState) -> PlayerState:
        if any(c is target for c in state.a.characters):
            return state.a
        return state.b

    @staticmethod
    def _charge(player: PlayerState, payment: PaymentPlan) -> None:
        for kind, qty in payment.debit.items():
            player.essences[kind] = player.essences.get(kind, 0) - qty
