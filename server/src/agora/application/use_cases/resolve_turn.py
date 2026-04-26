"""Use case: resolve a single turn for the current side."""

from __future__ import annotations

import copy

from agora.application.ports import CharacterRepository, RandomSource
from agora.domain.character import Effect, Skill
from agora.domain.enums import (
    AFFLICTION_NAMES,
    EffectKind,
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
    effects=[Effect(kind=EffectKind.INVULNERABLE, duration=1)],
)


def resolve_turn(
    state: MatchState,
    actions: list[Action],
    repository: CharacterRepository,
    rng: RandomSource,
) -> tuple[MatchState, list[Event]]:
    """Resolve the current side's turn and return the new state plus event log.

    Order of operations:
      1. Tick statuses (DoT, expirations).
      2. Validate and execute actions in submitted order.
      3. Decrement cooldowns for the active side.
      4. Check end of match.
      5. Switch sides and roll new essences for the new active side.
    """
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

    _tick_statuses(active, events)
    _tick_statuses(opponent, events)
    if _check_end(new_state, events):
        return new_state, events

    for action in actions:
        actor = _find_character(active, action.character_id)
        if actor is None or not actor.alive:
            events.append(
                Event(
                    kind="invalid_action",
                    details={"reason": "dead_or_missing", "character": action.character_id},
                )
            )
            continue

        if _is_stunned(actor):
            events.append(
                Event(
                    kind="invalid_action",
                    details={"reason": "stunned", "character": actor.id},
                )
            )
            continue

        skill = _resolve_skill(repository, actor.id, action.skill_id)
        if skill is None:
            events.append(
                Event(
                    kind="invalid_action",
                    details={"reason": "unknown_skill", "skill": action.skill_id},
                )
            )
            continue

        if actor.cooldowns.get(skill.id, 0) > 0:
            events.append(
                Event(
                    kind="invalid_action",
                    details={"reason": "on_cooldown", "skill": skill.id},
                )
            )
            continue

        if not _pay_cost(active, skill, action):
            events.append(
                Event(
                    kind="invalid_action",
                    details={"reason": "insufficient_essence", "skill": skill.id},
                )
            )
            continue

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

        targets = _resolve_targets(skill, actor, action, active, opponent)
        for target in targets:
            target_owner = _owner_of(new_state, target)
            for effect in skill.effects:
                _apply_effect(
                    effect=effect,
                    source=actor,
                    target=target,
                    target_owner=target_owner,
                    events=events,
                    rng=rng,
                )

        if skill.cooldown > 0:
            actor.cooldowns[skill.id] = skill.cooldown

    _decrement_cooldowns(active)

    if _check_end(new_state, events):
        return new_state, events

    new_state.turn += 1
    new_state.current_side = Side.B if new_state.current_side is Side.A else Side.A
    new_active = new_state.player(new_state.current_side)
    alive_count = sum(1 for c in new_active.characters if c.alive)
    _generate_essences(new_active, alive_count, rng)

    events.append(
        Event(
            kind="turn_ended",
            details={"turn": state.turn, "side": active.side.value},
        )
    )
    return new_state, events


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #


def _find_character(player: PlayerState, character_id: str) -> CharacterState | None:
    return next((c for c in player.characters if c.id == character_id), None)


def _owner_of(state: MatchState, target: CharacterState) -> PlayerState:
    if any(c is target for c in state.a.characters):
        return state.a
    return state.b


def _resolve_skill(
    repository: CharacterRepository, character_id: str, skill_id: str
) -> Skill | None:
    if skill_id == DODGE_SKILL_ID:
        return DODGE_SKILL
    try:
        character = repository.get(character_id)
    except KeyError:
        return None
    return next((s for s in character.skills if s.id == skill_id), None)


def _is_stunned(character: CharacterState) -> bool:
    return any(s.name == "stun" for s in character.statuses)


def _is_invulnerable(character: CharacterState) -> bool:
    return any(s.name == "invulnerable" for s in character.statuses)


def _total_damage_reduction(character: CharacterState) -> int:
    return sum(s.value for s in character.statuses if s.name == "damage_reduction")


def _total_damage_buff(character: CharacterState) -> int:
    return sum(s.value for s in character.statuses if s.name == "damage_buff")


def _pay_cost(player: PlayerState, skill: Skill, action: Action) -> bool:
    """Validate that the supplied payment covers the cost and debit accordingly."""
    cost = dict(skill.cost)
    paid = dict(action.paid)

    # Specific costs must be paid in their own color.
    for kind, qty in cost.items():
        if kind is Essence.GENERIC:
            continue
        if paid.get(kind, 0) < qty:
            return False

    # Total paid must equal total cost.
    if sum(paid.values()) != sum(cost.values()):
        return False

    # Generic placeholder cannot be the actual payment.
    if Essence.GENERIC in paid:
        return False

    # Player must have the essences on hand.
    for kind, qty in paid.items():
        if player.essences.get(kind, 0) < qty:
            return False

    for kind, qty in paid.items():
        player.essences[kind] -= qty
    return True


def _resolve_targets(
    skill: Skill,
    actor: CharacterState,
    action: Action,
    active: PlayerState,
    opponent: PlayerState,
) -> list[CharacterState]:
    if skill.target is TargetKind.SELF:
        return [actor]
    if skill.target is TargetKind.ALL_ENEMIES:
        return [c for c in opponent.characters if c.alive]
    if skill.target is TargetKind.ALL_ALLIES:
        return [c for c in active.characters if c.alive]
    if skill.target is TargetKind.SINGLE_ENEMY:
        if not action.target_ids:
            return []
        target = _find_character(opponent, action.target_ids[0])
        return [target] if target and target.alive else []
    if skill.target is TargetKind.SINGLE_ALLY:
        if not action.target_ids:
            return []
        target = _find_character(active, action.target_ids[0])
        return [target] if target and target.alive else []
    return []


def _apply_effect(
    *,
    effect: Effect,
    source: CharacterState,
    target: CharacterState,
    target_owner: PlayerState,
    events: list[Event],
    rng: RandomSource,
) -> None:
    if effect.kind is EffectKind.DAMAGE:
        if _is_invulnerable(target) and not effect.true:
            return
        damage = effect.value + _total_damage_buff(source)
        if not effect.piercing:
            damage = max(0, damage - _total_damage_reduction(target))
            if target.shield > 0:
                absorbed = min(target.shield, damage)
                target.shield -= absorbed
                damage -= absorbed
        target.hp = max(0, target.hp - damage)
        events.append(
            Event(
                kind="damage",
                details={"source": source.id, "target": target.id, "value": damage},
            )
        )
        if not target.alive:
            events.append(Event(kind="character_defeated", details={"character": target.id}))
        return

    if effect.kind is EffectKind.HEAL:
        before = target.hp
        target.hp = min(target.hp_max, target.hp + effect.value)
        events.append(
            Event(
                kind="heal",
                details={"target": target.id, "value": target.hp - before},
            )
        )
        return

    if effect.kind is EffectKind.INVULNERABLE:
        target.statuses.append(ActiveStatus(name="invulnerable", duration=effect.duration))
        events.append(
            Event(
                kind="status_applied",
                details={"character": target.id, "status": "invulnerable", "duration": effect.duration},
            )
        )
        return

    if effect.kind is EffectKind.DAMAGE_REDUCTION:
        target.statuses.append(
            ActiveStatus(name="damage_reduction", duration=effect.duration, value=effect.value)
        )
        events.append(
            Event(
                kind="status_applied",
                details={
                    "character": target.id,
                    "status": "damage_reduction",
                    "duration": effect.duration,
                    "value": effect.value,
                },
            )
        )
        return

    if effect.kind is EffectKind.DAMAGE_BUFF:
        target.statuses.append(
            ActiveStatus(name="damage_buff", duration=effect.duration, value=effect.value)
        )
        events.append(
            Event(
                kind="status_applied",
                details={
                    "character": target.id,
                    "status": "damage_buff",
                    "duration": effect.duration,
                    "value": effect.value,
                },
            )
        )
        return

    if effect.kind is EffectKind.DESTRUCTIBLE_SHIELD:
        target.shield += effect.value
        events.append(
            Event(
                kind="status_applied",
                details={"character": target.id, "status": "shield", "value": effect.value},
            )
        )
        return

    if effect.kind is EffectKind.STATUS:
        if effect.status is None:
            return
        target.statuses.append(
            ActiveStatus(
                name=effect.status,
                duration=effect.duration,
                value=effect.value,
                source=source.id,
            )
        )
        events.append(
            Event(
                kind="status_applied",
                details={
                    "character": target.id,
                    "status": effect.status,
                    "duration": effect.duration,
                    "value": effect.value,
                },
            )
        )
        return

    if effect.kind is EffectKind.ESSENCE_DRAIN:
        for _ in range(effect.value):
            available = [
                e for e in ROLLABLE_ESSENCES if target_owner.essences.get(e, 0) > 0
            ]
            if not available:
                break
            chosen = Essence(rng.choice([e.value for e in available]))
            target_owner.essences[chosen] -= 1
            events.append(
                Event(
                    kind="essence_drained",
                    details={"side": target_owner.side.value, "essence": chosen.value},
                )
            )
        return

    if effect.kind is EffectKind.REMOVE_AFFLICTIONS:
        target.statuses = [s for s in target.statuses if s.name not in AFFLICTION_NAMES]
        events.append(
            Event(
                kind="status_expired",
                details={"character": target.id, "removed": "afflictions"},
            )
        )
        return


def _tick_statuses(player: PlayerState, events: list[Event]) -> None:
    """Apply DoT/HoT and decrement durations. Statuses with duration 0 are removed."""
    for character in player.characters:
        if not character.alive:
            continue

        for status in character.statuses:
            if status.name == "poison" and status.value > 0:
                character.hp = max(0, character.hp - status.value)
                events.append(
                    Event(
                        kind="damage",
                        details={"source": "poison", "target": character.id, "value": status.value},
                    )
                )
            elif status.name == "regen" and status.value > 0:
                before = character.hp
                character.hp = min(character.hp_max, character.hp + status.value)
                events.append(
                    Event(
                        kind="heal",
                        details={"target": character.id, "value": character.hp - before},
                    )
                )

        if not character.alive:
            events.append(Event(kind="character_defeated", details={"character": character.id}))

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


def _decrement_cooldowns(player: PlayerState) -> None:
    for character in player.characters:
        for skill_id in list(character.cooldowns.keys()):
            character.cooldowns[skill_id] = max(0, character.cooldowns[skill_id] - 1)
            if character.cooldowns[skill_id] == 0:
                del character.cooldowns[skill_id]


def _generate_essences(player: PlayerState, count: int, rng: RandomSource) -> None:
    options = [e.value for e in ROLLABLE_ESSENCES]
    for _ in range(count):
        chosen = Essence(rng.choice(options))
        player.essences[chosen] = player.essences.get(chosen, 0) + 1


def _check_end(state: MatchState, events: list[Event]) -> bool:
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
