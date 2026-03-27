from __future__ import annotations

from datetime import UTC, datetime
from functools import partial
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship

from . import Base, now

if TYPE_CHECKING:
    from . import LeagueDeck  # noqa: F401


class LeagueProfile(Base):
    """Tracks per-guild player state, currently just the selected deck."""

    __tablename__ = "league_profiles"

    guild_xid = Column(
        BigInteger,
        ForeignKey("guilds.xid", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        doc="Discord guild this profile belongs to",
    )
    user_xid = Column(
        BigInteger,
        ForeignKey("users.xid", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        doc="Discord user this profile belongs to",
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
    current_deck_id = Column(
        Integer,
        ForeignKey("league_decks.id", ondelete="SET NULL"),
        nullable=True,
        doc="The player's currently selected deck, or NULL if none",
    )

    current_deck = relationship(
        "LeagueDeck",
        doc="The player's currently selected deck object",
    )
