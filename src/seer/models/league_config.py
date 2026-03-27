from __future__ import annotations

from datetime import UTC, datetime
from functools import partial

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer
from sqlalchemy.sql.expression import true

from . import Base, now


class LeagueGuildConfig(Base):
    """Per-guild configuration for the league/EDH match-tracking system."""

    __tablename__ = "league_guild_configs"

    guild_xid = Column(
        BigInteger,
        primary_key=True,
        nullable=False,
        doc="The external Discord guild ID this config belongs to",
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
        default=10,
        server_default="10",
        doc="Minimum confirmed matches required to appear on the leaderboard",
    )
    points_gained = Column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
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
        default=0,
        server_default="0",
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
        default=100,
        server_default="100",
        doc="Offset added to displayed point totals",
    )
    deck_limit = Column(
        Integer,
        nullable=False,
        default=50,
        server_default="50",
        doc="Maximum number of decks a player may register",
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
        doc=(
            "Hours after which unconfirmed players are DMed a reminder. "
            "Set to 0 to disable reminders."
        ),
    )
