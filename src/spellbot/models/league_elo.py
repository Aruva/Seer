from __future__ import annotations

from datetime import UTC, datetime
from functools import partial

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer

from . import Base, now


class LeagueElo(Base):
    """Tracks per-guild ELO ratings for EDH league players.

    ELO is scoped to the guild (not per-channel) so a player's rating
    reflects their overall standing across all EDH league activity on
    that server.  Starting ELO is 1500; floor is 100.
    """

    __tablename__ = "league_elos"

    guild_xid = Column(
        BigInteger,
        ForeignKey("guilds.xid", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        doc="Discord guild this ELO belongs to",
    )
    user_xid = Column(
        BigInteger,
        ForeignKey("users.xid", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        doc="Discord user this ELO belongs to",
    )
    elo = Column(
        Integer,
        nullable=False,
        default=1500,
        server_default="1500",
        doc="Current ELO rating (new players start at 1500)",
    )
    games_played = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        doc="Total confirmed matches used to determine K-factor",
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
