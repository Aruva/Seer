from __future__ import annotations

from datetime import UTC, datetime
from functools import partial

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String

from . import Base, now


class WargameElo(Base):
    """Tracks per-guild, per-game-system ELO ratings for wargame players.

    ELO is scoped to (guild, game_system) so a player's Warmachine rating
    and 40K rating are tracked independently.  Starting ELO is 1500; floor
    is 100.
    """

    __tablename__ = "wargame_elos"

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
    game_system = Column(
        String(64),
        primary_key=True,
        nullable=False,
        doc="Game system slug (e.g. 'warmachine', 'warhammer40k', or custom)",
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
