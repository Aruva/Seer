from __future__ import annotations

from datetime import UTC, datetime
from functools import partial
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import false

from . import Base, now

if TYPE_CHECKING:
    from . import LeagueDeck, LeagueSeason  # noqa: F401


class LeagueMatch(Base):
    """A logged 4-player EDH match awaiting or having received confirmation."""

    __tablename__ = "league_matches"

    id = Column(
        Integer,
        autoincrement=True,
        primary_key=True,
        nullable=False,
        doc="Internal match ID",
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
        ForeignKey("league_seasons.id", ondelete="CASCADE"),
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
        doc="Discord message ID of the match confirmation embed",
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
        "LeagueSeason",
        back_populates="matches",
        doc="The season this match is part of",
    )
    players = relationship(
        "LeagueMatchPlayer",
        back_populates="match",
        cascade="all, delete-orphan",
        doc="The players in this match",
    )

    @property
    def is_confirmed(self) -> bool:
        return bool(self.confirmed_at) and all(p.confirmed for p in self.players)

    @property
    def is_draw(self) -> bool:
        return self.winner_xid is None


class LeagueMatchPlayer(Base):
    """A single player's participation record in a league match."""

    __tablename__ = "league_match_players"

    id = Column(
        Integer,
        autoincrement=True,
        primary_key=True,
        nullable=False,
    )
    match_id = Column(
        Integer,
        ForeignKey("league_matches.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        doc="The match this player record belongs to",
    )
    user_xid = Column(
        BigInteger,
        nullable=False,
        index=True,
        doc="Discord user ID of the player",
    )
    deck_id = Column(
        Integer,
        ForeignKey("league_decks.id", ondelete="SET NULL"),
        nullable=True,
        doc="The deck the player used, if any",
    )
    confirmed = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
        doc="Whether this player has confirmed the match",
    )
    seat = Column(
        Integer,
        nullable=True,
        doc=(
            "Seat number (1–4) this player occupied. NULL when not recorded. "
            "Used to apply seat-bias correction to ELO calculations."
        ),
    )

    match = relationship(
        "LeagueMatch",
        back_populates="players",
        doc="The match this player record belongs to",
    )
    deck = relationship(
        "LeagueDeck",
        doc="The deck used by this player",
    )
