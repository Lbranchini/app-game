"""SQLAlchemy-backed match history.

Shares the engine with `SqlAlchemyPlayerRepository` so production deployments
hit a single connection pool. For dev each repository can be instantiated
independently (each `create_engine(...)` call manages its own pool).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import cast

from sqlalchemy import (
    DateTime,
    Engine,
    Integer,
    String,
    create_engine,
    or_,
    select,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    sessionmaker,
)
from sqlalchemy.pool import StaticPool

from agora.domain.match_record import MatchRecord


class _Base(DeclarativeBase):
    pass


class _MatchRow(_Base):
    __tablename__ = "matches"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    arena_id: Mapped[str] = mapped_column(String)
    side_a_player_id: Mapped[str] = mapped_column(String, index=True)
    side_b_player_id: Mapped[str] = mapped_column(String, index=True)
    team_a_json: Mapped[str] = mapped_column(String)
    team_b_json: Mapped[str] = mapped_column(String)
    winner: Mapped[str | None] = mapped_column(String, nullable=True)
    turns: Mapped[int] = mapped_column(Integer, default=0)
    seed: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


def _to_domain(row: _MatchRow) -> MatchRecord:
    return MatchRecord(
        id=row.id,
        arena_id=row.arena_id,
        side_a_player_id=row.side_a_player_id,
        side_b_player_id=row.side_b_player_id,
        team_a=json.loads(row.team_a_json),
        team_b=json.loads(row.team_b_json),
        winner=row.winner,
        turns=row.turns,
        seed=row.seed,
        started_at=row.started_at,
        ended_at=row.ended_at,
    )


class SqlAlchemyMatchHistoryRepository:
    def __init__(self, database_url: str = "sqlite:///./agora.db") -> None:
        # In-memory SQLite databases live for the duration of one connection
        # by default — every session would see an empty DB. StaticPool shares
        # a single connection so the schema and rows persist across sessions.
        kwargs: dict[str, object] = {"future": True}
        if ":memory:" in database_url or database_url == "sqlite://":
            kwargs.update(
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        self._engine: Engine = create_engine(database_url, **kwargs)
        _Base.metadata.create_all(self._engine)
        self._session_factory = sessionmaker(
            bind=self._engine, expire_on_commit=False, future=True
        )

    def save(self, record: MatchRecord) -> None:
        with self._session_factory() as session:
            row = _MatchRow(
                id=record.id,
                arena_id=record.arena_id,
                side_a_player_id=record.side_a_player_id,
                side_b_player_id=record.side_b_player_id,
                team_a_json=json.dumps(record.team_a),
                team_b_json=json.dumps(record.team_b),
                winner=record.winner,
                turns=record.turns,
                seed=record.seed,
                started_at=record.started_at,
                ended_at=record.ended_at,
            )
            session.merge(row)  # idempotent: same id replaces.
            session.commit()

    def list_recent(
        self, *, player_id: str | None = None, limit: int = 20
    ) -> list[MatchRecord]:
        with self._session_factory() as session:
            stmt = select(_MatchRow)
            if player_id is not None:
                stmt = stmt.where(
                    or_(
                        _MatchRow.side_a_player_id == player_id,
                        _MatchRow.side_b_player_id == player_id,
                    )
                )
            stmt = stmt.order_by(_MatchRow.started_at.desc()).limit(limit)
            rows = cast(list[_MatchRow], list(session.execute(stmt).scalars()))
            return [_to_domain(r) for r in rows]
