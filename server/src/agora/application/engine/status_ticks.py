"""Polymorphic per-turn status handlers.

A status that does something at the start of each turn (DoT, HoT, ...) gets
its own subclass. Statuses that exist only as flags (stun, silence, marked)
are read by the resolver via predicates and don't need a tick handler.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from agora.domain.events import Event
from agora.domain.match import ActiveStatus, CharacterState


class StatusTickHandler(ABC):
    @abstractmethod
    def tick(
        self, status: ActiveStatus, character: CharacterState, events: list[Event]
    ) -> None: ...


class PoisonTick(StatusTickHandler):
    def tick(
        self, status: ActiveStatus, character: CharacterState, events: list[Event]
    ) -> None:
        if status.value <= 0:
            return
        character.hp = max(0, character.hp - status.value)
        events.append(
            Event(
                kind="damage",
                details={"source": "poison", "target": character.id, "value": status.value},
            )
        )


class BleedTick(StatusTickHandler):
    """Flat DoT, identical mechanic to poison but separate so cleanses can target it
    differently in the future and so the kill-feed reads `bleed` not `poison`."""

    def tick(
        self, status: ActiveStatus, character: CharacterState, events: list[Event]
    ) -> None:
        if status.value <= 0:
            return
        character.hp = max(0, character.hp - status.value)
        events.append(
            Event(
                kind="damage",
                details={"source": "bleed", "target": character.id, "value": status.value},
            )
        )


class RegenTick(StatusTickHandler):
    def tick(
        self, status: ActiveStatus, character: CharacterState, events: list[Event]
    ) -> None:
        if status.value <= 0:
            return
        before = character.hp
        character.hp = min(character.hp_max, character.hp + status.value)
        if character.hp != before:
            events.append(
                Event(
                    kind="heal",
                    details={"target": character.id, "value": character.hp - before},
                )
            )


STATUS_TICK_HANDLERS: dict[str, StatusTickHandler] = {
    "poison": PoisonTick(),
    "bleed": BleedTick(),
    "regen": RegenTick(),
}
