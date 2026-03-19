"""Add league ELO table and reminder_hours to league_guild_configs.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-03-18 00:00:00.000000

Changes:
  - Creates ``league_elos`` table tracking per-guild ELO ratings and
    games-played count for each EDH league player (default ELO = 1500).
  - Adds ``reminder_hours`` column to ``league_guild_configs`` so admins
    can tune (or disable) the unconfirmed-match reminder delay.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "league_elos",
        sa.Column("guild_xid", sa.BigInteger(), nullable=False),
        sa.Column("user_xid", sa.BigInteger(), nullable=False),
        sa.Column("elo", sa.Integer(), server_default="1500", nullable=False),
        sa.Column("games_played", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(now() at time zone 'utc')"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(now() at time zone 'utc')"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["guild_xid"], ["guilds.xid"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_xid"], ["users.xid"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("guild_xid", "user_xid"),
    )

    op.add_column(
        "league_guild_configs",
        sa.Column(
            "reminder_hours",
            sa.Integer(),
            server_default="24",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("league_guild_configs", "reminder_hours")
    op.drop_table("league_elos")
