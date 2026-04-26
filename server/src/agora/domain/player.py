"""Player aggregate.

Domain-level representation. The infrastructure layer maps this to whatever
database engine is in use (SQLite for dev, PostgreSQL in production).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_STARTERS: tuple[str, ...] = (
    "achilles",
    "athena",
    "thor",
    "anubis",
    "isis",
    "anansi",
    "joan_of_arc",
    "loki",
)


class Player(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str  # opaque uuid
    provider_subject: str  # `google:1234`, `apple:abcd`, ...
    email: str | None = None
    name: str | None = None
    elo: int = 1000
    unlocked_characters: list[str] = Field(default_factory=lambda: list(DEFAULT_STARTERS))
    progress: dict[str, int] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime | None = None
