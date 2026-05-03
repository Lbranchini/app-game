"""Game vocabulary as enums."""

from __future__ import annotations

from enum import Enum


class Essence(str, Enum):
    """Energy resource for skills. Four colors plus a generic slot."""

    VIGOR = "vigor"
    SPIRIT = "spirit"
    MIND = "mind"
    BLOOD = "blood"
    GENERIC = "generic"


ROLLABLE_ESSENCES: tuple[Essence, ...] = (
    Essence.VIGOR,
    Essence.SPIRIT,
    Essence.MIND,
    Essence.BLOOD,
)


class Archetype(str, Enum):
    DAMAGE_DEALER = "damage_dealer"
    HEALER = "healer"
    TANK = "tank"
    STUNNER = "stunner"
    DRAINER = "drainer"
    TRICKSTER = "trickster"
    SUPPORT = "support"
    LEADER = "leader"


class SkillKind(str, Enum):
    INSTANT = "instant"
    ONGOING = "ongoing"
    CONTROL = "control"


class TargetKind(str, Enum):
    SINGLE_ENEMY = "single_enemy"
    ALL_ENEMIES = "all_enemies"
    SINGLE_ALLY = "single_ally"
    ALL_ALLIES = "all_allies"
    SELF = "self"


class EffectKind(str, Enum):
    DAMAGE = "damage"
    HEAL = "heal"
    INVULNERABLE = "invulnerable"
    DAMAGE_REDUCTION = "damage_reduction"
    DAMAGE_BUFF = "damage_buff"
    DESTRUCTIBLE_SHIELD = "destructible_shield"
    STATUS = "status"
    ESSENCE_DRAIN = "essence_drain"
    REMOVE_AFFLICTIONS = "remove_afflictions"


class DamageClass(str, Enum):
    PHYSICAL = "physical"
    MAGICAL = "magical"
    HOLY = "holy"
    MENTAL = "mental"


class Side(str, Enum):
    A = "A"
    B = "B"


# Status names used as opaque strings in data files.
# Keep this set in sync with the engine handlers.
# `stealth` is intentionally NOT here — it's a self-buff, not an affliction,
# so a `remove_afflictions` cleanse must not strip it from the stealthed
# character.
AFFLICTION_NAMES: frozenset[str] = frozenset(
    {"poison", "bleed", "stun", "silence", "disarm", "drained", "marked", "vulnerable"}
)
