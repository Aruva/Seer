from __future__ import annotations

from datetime import UTC, datetime
from functools import partial
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import false

from . import Base, now

if TYPE_CHECKING:
    from . import WargameArmy, WargameSeason  # noqa: F401


class WargameMatch(Base):
    """A logged 1v1 wargame match pending or having received confirmation."""

    __tablename__ = "wargame_matches"

    id = Column(
        Integer,
        autoincrement=True,
        primary_key=True,
        nullable=False,
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=partial(datetime.now, UTC),
        server_default=now,
        index=True,
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=partial(datetime.now, UTC),
        server_default=now,
        onupdate=partial(datetime.now, UTC),
    )
    guild_xid = Column(
        BigInteger,
        ForeignKey("guilds.xid", ondelete="CASCADE"),
        index=True,
        nullable=False,
        doc="Discord guild this match belongs to",
    )
    season_id = Column(
        Integer,
        ForeignKey("wargame_seasons.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        doc="Season this match belongs to",
    )
    winner_xid = Column(
        BigInteger,
        nullable=True,
        doc="Discord user ID of the winner, or NULL if the match was a draw",
    )
    channel_xid = Column(
        BigInteger,
        nullable=True,
        doc="Discord channel ID where the match was logged",
    )
    message_xid = Column(
        BigInteger,
        nullable=True,
        doc="Discord message ID of the confirmation embed",
    )
    dispute_thread_xid = Column(
        BigInteger,
        nullable=True,
        doc="Discord thread ID of the dispute thread, if any",
    )
    confirmed_at = Column(
        DateTime,
        nullable=True,
        doc="UTC timestamp when the match was fully confirmed",
    )

    season = relationship(
        "WargameSeason",
        back_populates="matches",
        doc="The season this match is part of",
    )
    players = relationship(
        "WargameMatchPlayer",
        back_populates="match",
        cascade="all, delete-orphan",
        doc="The two players in this match",
    )

    @property
    def is_confirmed(self) -> bool:
        return bool(self.confirmed_at) and all(p.confirmed for p in self.players)

    @property
    def is_draw(self) -> bool:
        return self.winner_xid is None


class WargameMatchPlayer(Base):
    """One player's participation record in a wargame match."""

    __tablename__ = "wargame_match_players"

    id = Column(
        Integer,
        autoincrement=True,
        primary_key=True,
        nullable=False,
    )
    match_id = Column(
        Integer,
        ForeignKey("wargame_matches.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_xid = Column(
        BigInteger,
        nullable=False,
        index=True,
        doc="Discord user ID of the player",
    )
    army_id = Column(
        Integer,
        ForeignKey("wargame_armies.id", ondelete="SET NULL"),
        nullable=True,
        doc="The army the player used, if recorded",
    )
    confirmed = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
        doc="Whether this player has confirmed the match",
    )

    match = relationship(
        "WargameMatch",
        back_populates="players",
    )
    army = relationship(
        "WargameArmy",
        doc="The army used by this player",
    )
