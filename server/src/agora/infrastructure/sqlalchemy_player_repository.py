"""SQLAlchemy-backed `PlayerRepository`.

Uses SQLite for development and tests; the same model and queries run
unchanged on PostgreSQL once `DATABASE_URL` points there.

The schema is intentionally narrow at this stage: enough to upsert a row on
sign-in and read it back through `/auth/me`. Match history, missions, and
match-action logs are separate tables that arrive as those features land.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Engine,
    Integer,
    String,
    create_engine,
    func,
    select,
    update,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
)
from sqlalchemy.pool import StaticPool

from agora.domain.player import DEFAULT_STARTERS, Player


class _Base(DeclarativeBase):
    pass


class _PlayerRow(_Base):
    __tablename__ = "players"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    provider_subject: Mapped[str] = mapped_column(String, unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    elo: Mapped[int] = mapped_column(Integer, default=1000)
    unlocked_characters_json: Mapped[str] = mapped_column(
        String, default=lambda: json.dumps(list(DEFAULT_STARTERS))
    )
    progress_json: Mapped[str] = mapped_column(String, default="{}")
    # `func.now()` resolves on the database side so SQLite and Postgres both
    # store a coherent timestamp without Python clock drift across processes.
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True
    )
    last_seen: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True
    )


def _to_domain(row: _PlayerRow) -> Player:
    return Player(
        id=row.id,
        provider_subject=row.provider_subject,
        email=row.email,
        name=row.name,
        elo=row.elo,
        unlocked_characters=json.loads(row.unlocked_characters_json),
        progress=json.loads(row.progress_json),
        created_at=row.created_at,
        last_seen=row.last_seen,
    )


class SqlAlchemyPlayerRepository:
    def __init__(self, database_url: str = "sqlite:///./agora.db") -> None:
        # See note in SqlAlchemyMatchHistoryRepository: in-memory SQLite needs
        # StaticPool so all sessions hit the same connection.
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

    def upsert_by_provider(
        self,
        *,
        provider_subject: str,
        email: str | None,
        name: str | None,
    ) -> Player:
        with self._session_factory() as session:  # type: Session
            existing = session.execute(
                select(_PlayerRow).where(_PlayerRow.provider_subject == provider_subject)
            ).scalar_one_or_none()

            now = datetime.utcnow()
            if existing is None:
                row = _PlayerRow(
                    id=str(uuid.uuid4()),
                    provider_subject=provider_subject,
                    email=email,
                    name=name,
                    last_seen=now,
                )
                session.add(row)
                session.commit()
                session.refresh(row)
                return _to_domain(row)

            session.execute(
                update(_PlayerRow)
                .where(_PlayerRow.id == existing.id)
                .values(
                    email=email or existing.email,
                    name=name or existing.name,
                    last_seen=now,
                )
            )
            session.commit()
            session.refresh(existing)
            return _to_domain(existing)

    def get(self, player_id: str) -> Player:
        with self._session_factory() as session:
            row = session.get(_PlayerRow, player_id)
            if row is None:
                raise KeyError(player_id)
            return _to_domain(row)

    def get_by_provider(self, provider_subject: str) -> Player | None:
        with self._session_factory() as session:
            row = session.execute(
                select(_PlayerRow).where(_PlayerRow.provider_subject == provider_subject)
            ).scalar_one_or_none()
            return _to_domain(row) if row is not None else None

    def update_elo(self, player_id: str, new_elo: int) -> Player:
        with self._session_factory() as session:
            row = session.get(_PlayerRow, player_id)
            if row is None:
                raise KeyError(player_id)
            row.elo = new_elo
            session.commit()
            session.refresh(row)
            return _to_domain(row)

    def update_progress(self, player_id: str, progress: dict[str, int]) -> Player:
        with self._session_factory() as session:
            row = session.get(_PlayerRow, player_id)
            if row is None:
                raise KeyError(player_id)
            row.progress_json = json.dumps(progress)
            session.commit()
            session.refresh(row)
            return _to_domain(row)

    def update_unlocked(self, player_id: str, unlocked: list[str]) -> Player:
        with self._session_factory() as session:
            row = session.get(_PlayerRow, player_id)
            if row is None:
                raise KeyError(player_id)
            row.unlocked_characters_json = json.dumps(list(unlocked))
            session.commit()
            session.refresh(row)
            return _to_domain(row)
