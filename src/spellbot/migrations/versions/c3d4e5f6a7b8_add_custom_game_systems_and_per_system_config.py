"""add custom game systems and per-system wargame config

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-01-01 00:00:00.000000

Changes:
  1. Add wargame_custom_systems table for guild-defined game systems.
  2. Expand wargame_guild_configs PK to (guild_xid, game_system) so each
     game system can have independent settings.  Existing rows get
     game_system='*' (the global default sentinel).
  3. Add reminder_hours column to wargame_guild_configs.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. wargame_custom_systems ─────────────────────────────────────────────
    op.create_table(
        "wargame_custom_systems",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("guild_xid", sa.BigInteger(), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(now() at time zone 'utc')"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "guild_xid", "slug", name="uq_wargame_custom_systems_guild_slug"
        ),
    )
    op.create_index(
        "ix_wargame_custom_systems_guild_xid",
        "wargame_custom_systems",
        ["guild_xid"],
    )

    # ── 2. Expand wargame_guild_configs PK ───────────────────────────────────
    # Add game_system column, populate existing rows with '*', then rebuild PK.
    op.add_column(
        "wargame_guild_configs",
        sa.Column(
            "game_system",
            sa.String(64),
            nullable=True,  # temporarily nullable for the data migration
        ),
    )
    # Set all existing rows to the global default sentinel
    op.execute("UPDATE wargame_guild_configs SET game_system = '*'")
    # Make it NOT NULL now that all rows have a value
    op.alter_column("wargame_guild_configs", "game_system", nullable=False)

    # Drop the old single-column PK and create the composite PK
    op.drop_constraint("wargame_guild_configs_pkey", "wargame_guild_configs", type_="primary")
    op.create_primary_key(
        "wargame_guild_configs_pkey",
        "wargame_guild_configs",
        ["guild_xid", "game_system"],
    )

    # ── 3. Add reminder_hours to wargame_guild_configs ────────────────────────
    op.add_column(
        "wargame_guild_configs",
        sa.Column(
            "reminder_hours",
            sa.Integer(),
            server_default="24",
            nullable=False,
        ),
    )


def downgrade() -> None:
    # Remove reminder_hours
    op.drop_column("wargame_guild_configs", "reminder_hours")

    # Restore single-column PK (keep only '*' rows, one per guild)
    op.drop_constraint("wargame_guild_configs_pkey", "wargame_guild_configs", type_="primary")
    op.execute("DELETE FROM wargame_guild_configs WHERE game_system != '*'")
    op.create_primary_key(
        "wargame_guild_configs_pkey",
        "wargame_guild_configs",
        ["guild_xid"],
    )
    op.drop_column("wargame_guild_configs", "game_system")

    # Drop custom systems table
    op.drop_index("ix_wargame_custom_systems_guild_xid", table_name="wargame_custom_systems")
    op.drop_table("wargame_custom_systems")
