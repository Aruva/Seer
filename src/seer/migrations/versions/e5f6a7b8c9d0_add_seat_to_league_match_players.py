"""Add seat column to league_match_players for ELO seat-bias correction.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-03-18 00:01:00.000000

Adds a nullable ``seat`` (INTEGER 1–4) column to ``league_match_players``.
When present it records which turn-order seat a player occupied, enabling
the ELO calculator to apply the seat-bias correction derived from cEDH
tournament data (Seat 1 ≈ +6.5% win-rate vs baseline; Seat 4 ≈ -4.8%).

Existing rows default to NULL (no correction applied for historical matches).
"""

import sqlalchemy as sa
from alembic import op

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "league_match_players",
        sa.Column("seat", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("league_match_players", "seat")
