"""add infractions table

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-03-26 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b3c4d5e6f7a8"
down_revision = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "infractions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("guild_xid", sa.BigInteger(), nullable=False),
        sa.Column("user_xid", sa.BigInteger(), nullable=False),
        sa.Column("judge_xid", sa.BigInteger(), nullable=True),
        sa.Column("judge_name", sa.String(length=100), nullable=True),
        sa.Column("game_system", sa.String(length=50), nullable=False),
        sa.Column("infraction", sa.String(length=200), nullable=False),
        sa.Column("infraction_category", sa.String(length=100), nullable=False),
        sa.Column("penalty", sa.String(length=50), nullable=False),
        sa.Column("round", sa.String(length=10), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
            ["guild_xid"],
            ["guilds.xid"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_xid"],
            ["users.xid"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_infractions_guild_xid"), "infractions", ["guild_xid"])
    op.create_index(op.f("ix_infractions_user_xid"), "infractions", ["user_xid"])


def downgrade() -> None:
    op.drop_index(op.f("ix_infractions_user_xid"), table_name="infractions")
    op.drop_index(op.f("ix_infractions_guild_xid"), table_name="infractions")
    op.drop_table("infractions")
