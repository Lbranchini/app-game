"""Alembic migration environment.

Wires the two SQLAlchemy MetaData objects this project uses (one per
repository module) so `--autogenerate` sees every table. The database URL
comes from the same settings layer as the live app, so a single
`DATABASE_URL` env var drives both.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Wire the project's settings and metadata.
from agora.infrastructure.sqlalchemy_match_history_repository import (  # noqa: E402
    _Base as MatchBase,
)
from agora.infrastructure.sqlalchemy_player_repository import (  # noqa: E402
    _Base as PlayerBase,
)
from agora.interfaces.api.settings import get_settings  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Each `_Base` carries its own MetaData; alembic accepts a list and merges
# them at autogenerate time.
target_metadata = [PlayerBase.metadata, MatchBase.metadata]


def _resolved_url() -> str:
    cli_url = config.get_main_option("sqlalchemy.url")
    if cli_url:
        return cli_url
    return get_settings().database_url


def run_migrations_offline() -> None:
    """Emit SQL without a live DB connection — useful for review."""
    context.configure(
        url=_resolved_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Standard mode: open a connection and apply revisions in a transaction."""
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = _resolved_url()
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
