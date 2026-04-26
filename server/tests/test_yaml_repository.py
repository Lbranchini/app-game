"""Tests for YAML loading via the repository port implementation."""

from __future__ import annotations

from agora.domain.character import Character
from agora.domain.enums import EffectKind, Essence, SkillKind, TargetKind


def test_loads_achilles(achilles: Character) -> None:
    assert achilles.id == "achilles"
    assert achilles.base_hp == 110
    assert len(achilles.skills) == 3

    spear = achilles.skills[0]
    assert spear.id == "spear"
    assert spear.kind is SkillKind.INSTANT
    assert spear.target is TargetKind.SINGLE_ENEMY
    assert spear.cost == {Essence.VIGOR: 1}
    assert spear.effects[0].kind is EffectKind.DAMAGE
    assert spear.effects[0].value == 20


def test_athena_aegis_targets_all_allies(athena: Character) -> None:
    aegis = next(s for s in athena.skills if s.id == "aegis")
    assert aegis.target is TargetKind.ALL_ALLIES
    assert aegis.effects[0].kind is EffectKind.DESTRUCTIBLE_SHIELD
    assert aegis.effects[0].value == 25


def test_anubis_applies_poison(anubis: Character) -> None:
    wraps = anubis.skills[0]
    poison = next(e for e in wraps.effects if e.kind is EffectKind.STATUS)
    assert poison.status == "poison"
    assert poison.duration == 2
    assert poison.value == 10
