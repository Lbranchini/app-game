"""Polymorphic per-turn status handlers.

A status that does something at the start of each turn (DoT, HoT, drained,
...) gets its own subclass. Statuses that exist only as flags (stun,
silence, marked) are read by the resolver via predicates and don't need a
tick handler.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from agora.application.engine.context import StatusTickContext
from agora.domain.enums import Essence, ROLLABLE_ESSENCES
from agora.domain.events import Event


class StatusTickHandler(ABC):
    @abstractmethod
    def tick(self, ctx: StatusTickContext) -> None: ...


class PoisonTick(StatusTickHandler):
    def tick(self, ctx: StatusTickContext) -> None:
        if ctx.status.value <= 0:
            return
        ctx.character.hp = max(0, ctx.character.hp - ctx.status.value)
        # `source` carries the original applier so post-match telemetry can
        # credit them; `tick` keeps the status name for display.
        ctx.events.append(
            Event(
                kind="damage",
                details={
                    "source": ctx.status.source or "poison",
                    "tick": "poison",
                    "target": ctx.character.id,
                    "value": ctx.status.value,
                },
            )
        )


class BleedTick(StatusTickHandler):
    """Flat DoT, identical mechanic to poison but separate so cleanses can target it
    differently in the future and so the kill-feed reads `bleed` not `poison`."""

    def tick(self, ctx: StatusTickContext) -> None:
        if ctx.status.value <= 0:
            return
        ctx.character.hp = max(0, ctx.character.hp - ctx.status.value)
        ctx.events.append(
            Event(
                kind="damage",
                details={
                    "source": ctx.status.source or "bleed",
                    "tick": "bleed",
                    "target": ctx.character.id,
                    "value": ctx.status.value,
                },
            )
        )


class RegenTick(StatusTickHandler):
    def tick(self, ctx: StatusTickContext) -> None:
        if ctx.status.value <= 0:
            return
        before = ctx.character.hp
        ctx.character.hp = min(ctx.character.hp_max, ctx.character.hp + ctx.status.value)
        if ctx.character.hp != before:
            ctx.events.append(
                Event(
                    kind="heal",
                    details={
                        "source": ctx.status.source or "regen",
                        "tick": "regen",
                        "target": ctx.character.id,
                        "value": ctx.character.hp - before,
                    },
                )
            )


class DrainedTick(StatusTickHandler):
    """Each turn the affected character's side loses 1 random essence."""

    def tick(self, ctx: StatusTickContext) -> None:
        available = [
            e for e in ROLLABLE_ESSENCES if ctx.player.essences.get(e, 0) > 0
        ]
        if not available:
            return
        chosen = Essence(ctx.rng.choice([e.value for e in available]))
        ctx.player.essences[chosen] -= 1
        ctx.events.append(
            Event(
                kind="essence_drained",
                details={"side": ctx.player.side.value, "essence": chosen.value, "source": "drained_status"},
            )
        )


STATUS_TICK_HANDLERS: dict[str, StatusTickHandler] = {
    "poison": PoisonTick(),
    "bleed": BleedTick(),
    "regen": RegenTick(),
    "drained": DrainedTick(),
}
