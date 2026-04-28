"""Public catalog endpoint for unlock rules.

The frontend reads this once on the Characters page so it can render each
locked character with its description and a progress bar that pulls the
current value from `Player.progress`.

Predicates aren't serializable so the response only carries the
`character_id`, `description`, `progress_key`, and `target` of each rule.
Rules that rely solely on a custom predicate (no progress_key/target)
expose `null` for those fields.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from agora.application.use_cases.unlocks import DEFAULT_RULES

router = APIRouter(prefix="/unlocks", tags=["unlocks"])


class UnlockRulePayload(BaseModel):
    character_id: str
    description: str
    progress_key: str | None
    target: int | None


@router.get("/rules", response_model=list[UnlockRulePayload])
def list_rules() -> list[UnlockRulePayload]:
    return [
        UnlockRulePayload(
            character_id=rule.character_id,
            description=rule.description,
            progress_key=rule.progress_key,
            target=rule.target,
        )
        for rule in DEFAULT_RULES
    ]
