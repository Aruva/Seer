"""Add wargame tables: armies, seasons, profiles, matches, match players, guild config.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-17 00:01:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None

UTC_NOW = sa.text("(now() at time zone 'utc')")


def upgrade() -> None:
    # Per-guild wargame config (shared across all game systems)
    op.create_table(
        "wargame_guild_configs",
        sa.Column("guild_xid", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=UTC_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=UTC_NOW, nullable=False),
        sa.Column("minimum_games", sa.Integer(), server_default="5", nullable=False),
        sa.Column("points_gained", sa.Integer(), server_default="3", nullable=False),
        sa.Column("points_lost", sa.Integer(), server_default="0", nullable=False),
        sa.Column("points_per_draw", sa.Integer(), server_default="1", nullable=False),
        sa.Column("enable_draws", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("base_points", sa.Integer(), server_default="0", nullable=False),
        sa.Column("army_limit", sa.Integer(), server_default="20", nullable=False),
        sa.Column("dispute_role_xid", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["guild_xid"], ["guilds.xid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("guild_xid"),
    )

    # Wargame seasons (scoped to a game system)
    op.create_table(
        "wargame_seasons",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=UTC_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=UTC_NOW, nullable=False),
        sa.Column("guild_xid", sa.BigInteger(), nullable=False),
        sa.Column("game_system", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("start_date", sa.DateTime(), server_default=UTC_NOW, nullable=False),
        sa.Column("end_date", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["guild_xid"], ["guilds.xid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wargame_seasons_guild_xid", "wargame_seasons", ["guild_xid"])
    op.create_index("ix_wargame_seasons_game_system", "wargame_seasons", ["game_system"])

    # Armies (equivalent of decks, per game system)
    op.create_table(
        "wargame_armies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=UTC_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=UTC_NOW, nullable=False),
        sa.Column("guild_xid", sa.BigInteger(), nullable=False),
        sa.Column("user_xid", sa.BigInteger(), nullable=False),
        sa.Column("game_system", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("faction", sa.String(length=64), nullable=True),
        sa.Column("list_url", sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(["guild_xid"], ["guilds.xid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_xid"], ["users.xid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wargame_armies_guild_xid", "wargame_armies", ["guild_xid"])
    op.create_index("ix_wargame_armies_user_xid", "wargame_armies", ["user_xid"])
    op.create_index("ix_wargame_armies_game_system", "wargame_armies", ["game_system"])

    # Player profiles (current army per guild + user + game system)
    op.create_table(
        "wargame_profiles",
        sa.Column("guild_xid", sa.BigInteger(), nullable=False),
        sa.Column("user_xid", sa.BigInteger(), nullable=False),
        sa.Column("game_system", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=UTC_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=UTC_NOW, nullable=False),
        sa.Column("current_army_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["guild_xid"], ["guilds.xid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_xid"], ["users.xid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["current_army_id"], ["wargame_armies.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("guild_xid", "user_xid", "game_system"),
    )

    # Matches
    op.create_table(
        "wargame_matches",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=UTC_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=UTC_NOW, nullable=False),
        sa.Column("guild_xid", sa.BigInteger(), nullable=False),
        sa.Column("season_id", sa.Integer(), nullable=False),
        sa.Column("winner_xid", sa.BigInteger(), nullable=True),
        sa.Column("channel_xid", sa.BigInteger(), nullable=True),
        sa.Column("message_xid", sa.BigInteger(), nullable=True),
        sa.Column("dispute_thread_xid", sa.BigInteger(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["guild_xid"], ["guilds.xid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["season_id"], ["wargame_seasons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wargame_matches_guild_xid", "wargame_matches", ["guild_xid"])
    op.create_index("ix_wargame_matches_season_id", "wargame_matches", ["season_id"])
    op.create_index("ix_wargame_matches_created_at", "wargame_matches", ["created_at"])

    # Match players
    op.create_table(
        "wargame_match_players",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("user_xid", sa.BigInteger(), nullable=False),
        sa.Column("army_id", sa.Integer(), nullable=True),
        sa.Column(
            "confirmed",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["match_id"], ["wargame_matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["army_id"], ["wargame_armies.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wargame_match_players_match_id", "wargame_match_players", ["match_id"])
    op.create_index("ix_wargame_match_players_user_xid", "wargame_match_players", ["user_xid"])


def downgrade() -> None:
    op.drop_table("wargame_match_players")
    op.drop_table("wargame_matches")
    op.drop_table("wargame_profiles")
    op.drop_table("wargame_armies")
    op.drop_table("wargame_seasons")
    op.drop_table("wargame_guild_configs")
