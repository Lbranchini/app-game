"""Skill validation: cooldowns, costs, status restrictions.

Pulled out of the orchestrator so the rules are testable in isolation and
the resolver loop reads top-to-bottom.
"""

from __future__ import annotations

from dataclasses import dataclass

from agora.application.engine.status_predicates import (
    is_disarmed,
    is_silenced,
    is_stunned,
)
from agora.domain.character import Skill
from agora.domain.enums import DamageClass, EffectKind, Essence
from agora.domain.match import Action, CharacterState, PlayerState


@dataclass(frozen=True)
class ValidationFailure:
    reason: str


@dataclass(frozen=True)
class PaymentPlan:
    """Result of a successful cost validation: what to debit from the player."""

    debit: dict[Essence, int]


def is_skill_physical(skill: Skill) -> bool:
    return any(
        e.kind is EffectKind.DAMAGE and e.damage_class is DamageClass.PHYSICAL
        for e in skill.effects
    )


def is_skill_magical(skill: Skill) -> bool:
    return any(
        e.kind is EffectKind.DAMAGE and e.damage_class is DamageClass.MAGICAL
        for e in skill.effects
    )


def check_can_act(actor: CharacterState, skill: Skill) -> ValidationFailure | None:
    if is_stunned(actor):
        return ValidationFailure("stunned")
    if is_silenced(actor) and is_skill_magical(skill):
        return ValidationFailure("silenced")
    if is_disarmed(actor) and is_skill_physical(skill):
        return ValidationFailure("disarmed")
    return None


def check_cooldown(actor: CharacterState, skill: Skill) -> ValidationFailure | None:
    if actor.cooldowns.get(skill.id, 0) > 0:
        return ValidationFailure("on_cooldown")
    return None


def validate_payment(
    player: PlayerState, skill: Skill, action: Action
) -> PaymentPlan | ValidationFailure:
    """Validate the supplied payment matches the cost and the player can pay it.

    Pure: does not mutate the player. Caller debits using `PaymentPlan.debit`.
    """
    cost = dict(skill.cost)
    paid = dict(action.paid)

    for kind, qty in cost.items():
        if kind is Essence.GENERIC:
            continue
        if paid.get(kind, 0) < qty:
            return ValidationFailure("insufficient_essence")

    if sum(paid.values()) != sum(cost.values()):
        return ValidationFailure("insufficient_essence")

    if Essence.GENERIC in paid:
        return ValidationFailure("insufficient_essence")

    for kind, qty in paid.items():
        if player.essences.get(kind, 0) < qty:
            return ValidationFailure("insufficient_essence")

    return PaymentPlan(debit=dict(paid))
