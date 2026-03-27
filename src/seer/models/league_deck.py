from __future__ import annotations

from datetime import UTC, datetime
from functools import partial

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String

from . import Base, now

VALID_DECK_LIST_HOSTS = [
    "tappedout.net",
    "deckstats.net",
    "aetherhub.com",
    "moxfield.com",
    "tcgplayer.com",
    "archidekt.com",
    "scryfall.com",
]


class LeagueDeck(Base):
    """A deck registered by a player for league play."""

    __tablename__ = "league_decks"

    id = Column(
        Integer,
        autoincrement=True,
        primary_key=True,
        nullable=False,
        doc="Internal deck ID",
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
    guild_xid = Column(
        BigInteger,
        ForeignKey("guilds.xid", ondelete="CASCADE"),
        index=True,
        nullable=False,
        doc="Discord guild this deck belongs to",
    )
    user_xid = Column(
        BigInteger,
        ForeignKey("users.xid", ondelete="CASCADE"),
        index=True,
        nullable=False,
        doc="Discord user ID of the deck owner",
    )
    name = Column(
        String(64),
        nullable=False,
        doc="Display name for this deck",
    )
    deck_list = Column(
        String(256),
        nullable=True,
        doc="Optional URL pointing to the deck list on a supported site",
    )
