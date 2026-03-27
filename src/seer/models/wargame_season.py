from __future__ import annotations

from datetime import UTC, datetime
from functools import partial
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from . import Base, now

if TYPE_CHECKING:
    from . import WargameMatch  # noqa: F401


class WargameSeason(Base):
    """A named season for a specific wargame system within a guild."""

    __tablename__ = "wargame_seasons"

    id = Column(
        Integer,
        autoincrement=True,
        primary_key=True,
        nullable=False,
        doc="Internal season ID",
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
        doc="Discord guild this season belongs to",
    )
    game_system = Column(
        String(64),
        nullable=False,
        index=True,
        doc="Game system slug this season is for",
    )
    name = Column(
        String(100),
        nullable=False,
        doc="Display name for this season",
    )
    start_date = Column(
        DateTime,
        nullable=False,
        default=partial(datetime.now, UTC),
        server_default=now,
        doc="UTC timestamp when the season started",
    )
    end_date = Column(
        DateTime,
        nullable=True,
        doc="UTC timestamp when the season ended, or NULL if active",
    )

    matches = relationship(
        "WargameMatch",
        back_populates="season",
        doc="Matches logged during this season",
    )
