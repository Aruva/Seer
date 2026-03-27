"""add_wargame_elos

Adds the wargame_elos table for per-guild, per-game-system ELO tracking.

Revision ID: f1a2b3c4d5e6
Revises: e5f6a7b8c9d0
Create Date: 2025-01-01 00:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f1a2b3c4d5e6"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wargame_elos",
        sa.Column("guild_xid", sa.BigInteger(), nullable=False),
        sa.Column("user_xid", sa.BigInteger(), nullable=False),
        sa.Column("game_system", sa.String(64), nullable=False),
        sa.Column(
            "elo",
            sa.Integer(),
            nullable=False,
            server_default="1500",
        ),
        sa.Column(
            "games_played",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["guild_xid"],
            ["guilds.xid"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_xid"],
            ["users.xid"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("guild_xid", "user_xid", "game_system"),
    )
    op.create_index(
        "ix_wargame_elos_guild_xid",
        "wargame_elos",
        ["guild_xid"],
        unique=False,
    )
    op.create_index(
        "ix_wargame_elos_user_xid",
        "wargame_elos",
        ["user_xid"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_wargame_elos_user_xid", table_name="wargame_elos")
    op.drop_index("ix_wargame_elos_guild_xid", table_name="wargame_elos")
    op.drop_table("wargame_elos")
