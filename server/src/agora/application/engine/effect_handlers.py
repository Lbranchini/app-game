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
        if has_invulnerable(target) and not effect.true:
            return

        damage = effect.value + total_damage_buff(ctx.source) + total_marked_bonus(target)
        if not effect.piercing:
            damage = max(0, damage - total_damage_reduction(target))
            if target.shield > 0:
                absorbed = min(target.shield, damage)
                target.shield -= absorbed
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
                details={"target": target.id, "value": target.hp - before},
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
}
