"""Add league tables: seasons, decks, profiles, matches, match players, guild config.

Revision ID: a1b2c3d4e5f6
Revises: a53eae0a3e4a
Create Date: 2026-03-17 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "a53eae0a3e4a"
branch_labels = None
depends_on = None

UTC_NOW = sa.text("(now() at time zone 'utc')")


def upgrade() -> None:
    # Per-guild league configuration
    op.create_table(
        "league_guild_configs",
        sa.Column("guild_xid", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=UTC_NOW,
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=UTC_NOW,
            nullable=False,
        ),
        sa.Column(
            "minimum_games",
            sa.Integer(),
            server_default="10",
            nullable=False,
        ),
        sa.Column(
            "points_gained",
            sa.Integer(),
            server_default="1",
            nullable=False,
        ),
        sa.Column(
            "points_lost",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "points_per_draw",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "enable_draws",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "base_points",
            sa.Integer(),
            server_default="100",
            nullable=False,
        ),
        sa.Column(
            "deck_limit",
            sa.Integer(),
            server_default="50",
            nullable=False,
        ),
        sa.Column("dispute_role_xid", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(
            ["guild_xid"],
            ["guilds.xid"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("guild_xid"),
    )

    # Seasons
    op.create_table(
        "league_seasons",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=UTC_NOW,
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=UTC_NOW,
            nullable=False,
        ),
        sa.Column("guild_xid", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "start_date",
            sa.DateTime(),
            server_default=UTC_NOW,
            nullable=False,
        ),
        sa.Column("end_date", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["guild_xid"],
            ["guilds.xid"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_league_seasons_guild_xid", "league_seasons", ["guild_xid"])

    # Decks
    op.create_table(
        "league_decks",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=UTC_NOW,
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=UTC_NOW,
            nullable=False,
        ),
        sa.Column("guild_xid", sa.BigInteger(), nullable=False),
        sa.Column("user_xid", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("deck_list", sa.String(length=256), nullable=True),
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
    op.create_index("ix_league_decks_guild_xid", "league_decks", ["guild_xid"])
    op.create_index("ix_league_decks_user_xid", "league_decks", ["user_xid"])

    # Player profiles (current deck selection)
    op.create_table(
        "league_profiles",
        sa.Column("guild_xid", sa.BigInteger(), nullable=False),
        sa.Column("user_xid", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=UTC_NOW,
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=UTC_NOW,
            nullable=False,
        ),
        sa.Column("current_deck_id", sa.Integer(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["current_deck_id"],
            ["league_decks.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("guild_xid", "user_xid"),
    )

    # Matches
    op.create_table(
        "league_matches",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=UTC_NOW,
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=UTC_NOW,
            nullable=False,
        ),
        sa.Column("guild_xid", sa.BigInteger(), nullable=False),
        sa.Column("season_id", sa.Integer(), nullable=False),
        sa.Column("winner_xid", sa.BigInteger(), nullable=True),
        sa.Column("channel_xid", sa.BigInteger(), nullable=True),
        sa.Column("message_xid", sa.BigInteger(), nullable=True),
        sa.Column("dispute_thread_xid", sa.BigInteger(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["guild_xid"],
            ["guilds.xid"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["season_id"],
            ["league_seasons.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_league_matches_guild_xid", "league_matches", ["guild_xid"])
    op.create_index("ix_league_matches_season_id", "league_matches", ["season_id"])
    op.create_index("ix_league_matches_created_at", "league_matches", ["created_at"])

    # Match players
    op.create_table(
        "league_match_players",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("user_xid", sa.BigInteger(), nullable=False),
        sa.Column("deck_id", sa.Integer(), nullable=True),
        sa.Column(
            "confirmed",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["match_id"],
            ["league_matches.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["deck_id"],
            ["league_decks.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_league_match_players_match_id", "league_match_players", ["match_id"])
    op.create_index("ix_league_match_players_user_xid", "league_match_players", ["user_xid"])


def downgrade() -> None:
    op.drop_table("league_match_players")
    op.drop_table("league_matches")
    op.drop_table("league_profiles")
    op.drop_table("league_decks")
    op.drop_table("league_seasons")
    op.drop_table("league_guild_configs")
