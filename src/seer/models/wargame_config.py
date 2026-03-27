from __future__ import annotations

from datetime import UTC, datetime
from functools import partial

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql.expression import true

from . import Base, now

# Sentinel value meaning "global default applies to all game systems"
WARGAME_CONFIG_GLOBAL = "*"


class WargameGuildConfig(Base):
    """Per-guild, per-game-system configuration for the wargame league.

    Rows with game_system='*' act as the global default for any system that
    does not have its own explicit row.  The service layer handles fallback.
    """

    __tablename__ = "wargame_guild_configs"

    guild_xid = Column(
        BigInteger,
        primary_key=True,
        nullable=False,
        doc="The external Discord guild ID this config belongs to",
    )
    game_system = Column(
        String(64),
        primary_key=True,
        nullable=False,
        default=WARGAME_CONFIG_GLOBAL,
        server_default=WARGAME_CONFIG_GLOBAL,
        doc=(
            "Game system slug this config applies to, "
            "or '*' for the guild-wide default"
        ),
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=partial(datetime.now, UTC),
        server_default=now,
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=partial(datetime.now, UTC),
        server_default=now,
        onupdate=partial(datetime.now, UTC),
    )
    minimum_games = Column(
        Integer,
        nullable=False,
        default=5,
        server_default="5",
        doc="Minimum confirmed matches required to appear on the leaderboard",
    )
    points_gained = Column(
        Integer,
        nullable=False,
        default=3,
        server_default="3",
        doc="Points awarded per match win",
    )
    points_lost = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        doc="Points deducted per match loss",
    )
    points_per_draw = Column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
        doc="Points awarded per draw",
    )
    enable_draws = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
        doc="Whether players may log matches as draws",
    )
    base_points = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        doc="Offset added to displayed point totals",
    )
    army_limit = Column(
        Integer,
        nullable=False,
        default=20,
        server_default="20",
        doc="Maximum number of armies a player may register",
    )
    dispute_role_xid = Column(
        BigInteger,
        nullable=True,
        doc="Optional Discord role ID added to dispute threads",
    )
    reminder_hours = Column(
        Integer,
        nullable=False,
        default=24,
        server_default="24",
        doc="Hours after which unconfirmed players are sent a reminder DM",
    )
