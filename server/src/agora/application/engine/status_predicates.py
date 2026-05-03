"""Pure predicates over a CharacterState's statuses.

Kept separate so handlers can import each other without cycles.
"""

from __future__ import annotations

from agora.domain.match import CharacterState


def has_status(character: CharacterState, name: str) -> bool:
    return any(s.name == name for s in character.statuses)


def has_invulnerable(character: CharacterState) -> bool:
    return has_status(character, "invulnerable")


def is_stunned(character: CharacterState) -> bool:
    return has_status(character, "stun")


def is_silenced(character: CharacterState) -> bool:
    return has_status(character, "silence")


def is_disarmed(character: CharacterState) -> bool:
    return has_status(character, "disarm")


def is_drained(character: CharacterState) -> bool:
    return has_status(character, "drained")


def is_stealthed(character: CharacterState) -> bool:
    """Stealth makes the character un-targetable by single-target enemy skills.

    Broken when the stealthed character attacks (see `MatchEngine`).
    """
    return has_status(character, "stealth")


def total_damage_reduction(character: CharacterState) -> int:
    return sum(s.value for s in character.statuses if s.name == "damage_reduction")


def total_damage_buff(character: CharacterState) -> int:
    return sum(s.value for s in character.statuses if s.name == "damage_buff")


def total_marked_bonus(character: CharacterState) -> int:
    """Sum of `value` across `marked` statuses (extra flat damage taken)."""
    return sum(s.value for s in character.statuses if s.name == "marked")
