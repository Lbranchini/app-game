"""Polymorphic effect handlers.

One subclass per `EffectKind`. The `MatchEngine` looks up the handler for the
effect's kind and delegates resolution to it. Adding a new kind = adding a
subclass + registering it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from agora.application.engine.context import EffectContext
from agora.application.engine.status_predicates import (
    has_invulnerable,
    has_status,
    total_damage_buff,
    total_damage_reduction,
    total_marked_bonus,
)
from agora.domain.character import Effect
from agora.domain.enums import AFFLICTION_NAMES, EffectKind, Essence, ROLLABLE_ESSENCES
from agora.domain.events import Event
from agora.domain.match import ActiveStatus


class EffectHandler(ABC):
    """Base class for every kind of effect a skill can carry."""

    @abstractmethod
    def apply(self, effect: Effect, ctx: EffectContext) -> None: ...


class DamageHandler(EffectHandler):
    def apply(self, effect: Effect, ctx: EffectContext) -> None:
        target = ctx.target

        # Reflective: a one-shot status. The next damage skill aimed at this
        # character bounces back to its source. Inevitable damage cannot be
        # reflected — the engine treats `effect.true` as inevitable for now.
        reflect = next((s for s in target.statuses if s.name == "reflective"), None)
        if reflect is not None and not effect.true:
            target.statuses.remove(reflect)
            ctx.events.append(
                Event(
                    kind="status_expired",
                    details={"character": target.id, "status": "reflective", "consumed": True},
                )
            )
            target = ctx.source  # bounce: the source takes its own hit

        if has_invulnerable(target) and not effect.true:
            return

        damage = effect.value + total_damage_buff(ctx.source) + total_marked_bonus(target)
        if not effect.piercing:
            damage = max(0, damage - total_damage_reduction(target))
            if target.shield > 0:
                absorbed = min(target.shield, damage)
                target.shield -= absorbed
                if target.shield == 0:
                    target.shield_source = None
                damage -= absorbed

        target.hp = max(0, target.hp - damage)
        ctx.events.append(
            Event(
                kind="damage",
                details={"source": ctx.source.id, "target": target.id, "value": damage},
            )
        )
        if not target.alive:
            ctx.events.append(
                Event(kind="character_defeated", details={"character": target.id})
            )


class HealHandler(EffectHandler):
    def apply(self, effect: Effect, ctx: EffectContext) -> None:
        target = ctx.target
        before = target.hp
        target.hp = min(target.hp_max, target.hp + effect.value)
        ctx.events.append(
            Event(
                kind="heal",
                details={
                    "source": ctx.source.id,
                    "target": target.id,
                    "value": target.hp - before,
                },
            )
        )


class _StatusApplyingHandler(EffectHandler):
    """Base for handlers that attach a single named status."""

    name: str = ""

    def _attach(self, *, ctx: EffectContext, duration: int, value: int) -> None:
        if has_status(ctx.target, "vulnerable") and self.name in {
            "invulnerable",
            "damage_reduction",
        }:
            ctx.events.append(
                Event(
                    kind="status_expired",
                    details={"character": ctx.target.id, "status": self.name, "blocked_by": "vulnerable"},
                )
            )
            return
        ctx.target.statuses.append(
            ActiveStatus(name=self.name, duration=duration, value=value, source=ctx.source.id)
        )
        ctx.events.append(
            Event(
                kind="status_applied",
                details={
                    "character": ctx.target.id,
                    "status": self.name,
                    "duration": duration,
                    "value": value,
                    "source": ctx.source.id,
                },
            )
        )


class InvulnerableHandler(_StatusApplyingHandler):
    name = "invulnerable"

    def apply(self, effect: Effect, ctx: EffectContext) -> None:
        self._attach(ctx=ctx, duration=effect.duration, value=0)


class DamageReductionHandler(_StatusApplyingHandler):
    name = "damage_reduction"

    def apply(self, effect: Effect, ctx: EffectContext) -> None:
        self._attach(ctx=ctx, duration=effect.duration, value=effect.value)


class DamageBuffHandler(_StatusApplyingHandler):
    name = "damage_buff"

    def apply(self, effect: Effect, ctx: EffectContext) -> None:
        self._attach(ctx=ctx, duration=effect.duration, value=effect.value)


class DestructibleShieldHandler(EffectHandler):
    def apply(self, effect: Effect, ctx: EffectContext) -> None:
        ctx.target.shield += effect.value
        ctx.target.shield_source = ctx.source.id
        ctx.events.append(
            Event(
                kind="status_applied",
                details={"character": ctx.target.id, "status": "shield", "value": effect.value},
            )
        )


class StatusHandler(EffectHandler):
    """Generic handler for arbitrary named statuses (poison, bleed, stun, ...)."""

    def apply(self, effect: Effect, ctx: EffectContext) -> None:
        if effect.status is None:
            return
        ctx.target.statuses.append(
            ActiveStatus(
                name=effect.status,
                duration=effect.duration,
                value=effect.value,
                source=ctx.source.id,
            )
        )
        ctx.events.append(
            Event(
                kind="status_applied",
                details={
                    "character": ctx.target.id,
                    "status": effect.status,
                    "duration": effect.duration,
                    "value": effect.value,
                    "source": ctx.source.id,
                },
            )
        )


class EssenceDrainHandler(EffectHandler):
    def apply(self, effect: Effect, ctx: EffectContext) -> None:
        for _ in range(effect.value):
            available = [
                e for e in ROLLABLE_ESSENCES if ctx.target_owner.essences.get(e, 0) > 0
            ]
            if not available:
                break
            chosen = Essence(ctx.rng.choice([e.value for e in available]))
            ctx.target_owner.essences[chosen] -= 1
            ctx.events.append(
                Event(
                    kind="essence_drained",
                    details={"side": ctx.target_owner.side.value, "essence": chosen.value},
                )
            )


class RemoveAfflictionsHandler(EffectHandler):
    def apply(self, effect: Effect, ctx: EffectContext) -> None:
        ctx.target.statuses = [
            s for s in ctx.target.statuses if s.name not in AFFLICTION_NAMES
        ]
        ctx.events.append(
            Event(
                kind="status_expired",
                details={"character": ctx.target.id, "removed": "afflictions"},
            )
        )


class CopyHandler(EffectHandler):
    """The `copy` modifier: the source borrows the target's last-used skill.

    The borrowed skill goes onto `source.granted_skills` for `effect.duration`
    of the source's turns. The engine's `_lookup_skill` checks that list
    before falling back to the source's native kit, so the source can
    submit `Action(skill_id=<copied id>)` on its next turn just like a
    normal skill — paying the original cost from its own essence pool.

    No-ops emit an `invalid_action` flavoured event so the player gets
    feedback when a target hasn't acted yet.
    """

    def apply(self, effect: Effect, ctx: EffectContext) -> None:
        target = ctx.target
        source = ctx.source
        if target.last_skill_id is None:
            ctx.events.append(
                Event(
                    kind="invalid_action",
                    details={
                        "reason": "copy_no_target_skill",
                        "character": source.id,
                        "target": target.id,
                    },
                )
            )
            return
        # Drop any existing copy of the same skill so re-casting copy on the
        # same target just refreshes the duration instead of stacking.
        source.granted_skills = [
            g for g in source.granted_skills if g.skill_id != target.last_skill_id
        ]
        from agora.domain.match import GrantedSkill

        duration = max(1, effect.duration)
        source.granted_skills.append(
            GrantedSkill(
                skill_id=target.last_skill_id,
                source_character_id=target.id,
                turns_remaining=duration,
            )
        )
        ctx.events.append(
            Event(
                kind="skill_granted",
                details={
                    "character": source.id,
                    "skill": target.last_skill_id,
                    "from": target.id,
                    "duration": duration,
                },
            )
        )


EFFECT_HANDLERS: dict[EffectKind, EffectHandler] = {
    EffectKind.DAMAGE: DamageHandler(),
    EffectKind.HEAL: HealHandler(),
    EffectKind.INVULNERABLE: InvulnerableHandler(),
    EffectKind.DAMAGE_REDUCTION: DamageReductionHandler(),
    EffectKind.DAMAGE_BUFF: DamageBuffHandler(),
    EffectKind.DESTRUCTIBLE_SHIELD: DestructibleShieldHandler(),
    EffectKind.STATUS: StatusHandler(),
    EffectKind.ESSENCE_DRAIN: EssenceDrainHandler(),
    EffectKind.REMOVE_AFFLICTIONS: RemoveAfflictionsHandler(),
    EffectKind.COPY: CopyHandler(),
}
