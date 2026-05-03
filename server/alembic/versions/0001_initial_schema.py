"""initial schema — players + matches tables.

Mirrors what `_Base.metadata.create_all()` produced through 0.1.0; this
becomes the reference baseline for any future Postgres deploy. New
columns or tables ship as their own revisions.

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-03
"""
from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "players",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("provider_subject", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("elo", sa.Integer(), nullable=False, server_default="1000"),
        sa.Column("unlocked_characters_json", sa.String(), nullable=False),
        sa.Column("progress_json", sa.String(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("last_seen", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_players_provider_subject", "players", ["provider_subject"], unique=True)
    op.create_index("ix_players_created_at", "players", ["created_at"], unique=False)
    op.create_index("ix_players_last_seen", "players", ["last_seen"], unique=False)

    op.create_table(
        "matches",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("arena_id", sa.String(), nullable=False),
        sa.Column("side_a_player_id", sa.String(), nullable=False),
        sa.Column("side_b_player_id", sa.String(), nullable=False),
        sa.Column("team_a_json", sa.String(), nullable=False),
        sa.Column("team_b_json", sa.String(), nullable=False),
        sa.Column("winner", sa.String(), nullable=True),
        sa.Column("turns", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("seed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "started_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("elo_delta_a", sa.Integer(), nullable=True),
        sa.Column("elo_delta_b", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_matches_side_a_player_id", "matches", ["side_a_player_id"])
    op.create_index("ix_matches_side_b_player_id", "matches", ["side_b_player_id"])
    op.create_index("ix_matches_started_at", "matches", ["started_at"])
    # Composite indexes for the per-player history page.
    op.create_index(
        "ix_matches_a_started_at", "matches", ["side_a_player_id", "started_at"]
    )
    op.create_index(
        "ix_matches_b_started_at", "matches", ["side_b_player_id", "started_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_matches_b_started_at", table_name="matches")
    op.drop_index("ix_matches_a_started_at", table_name="matches")
    op.drop_index("ix_matches_started_at", table_name="matches")
    op.drop_index("ix_matches_side_b_player_id", table_name="matches")
    op.drop_index("ix_matches_side_a_player_id", table_name="matches")
    op.drop_table("matches")

    op.drop_index("ix_players_last_seen", table_name="players")
    op.drop_index("ix_players_created_at", table_name="players")
    op.drop_index("ix_players_provider_subject", table_name="players")
    op.drop_table("players")
