from __future__ import annotations

from datetime import UTC, datetime
from functools import partial
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from . import Base, now

if TYPE_CHECKING:
    from . import LeagueMatch  # noqa: F401


class LeagueSeason(Base):
    """A named time-boxed season within which league matches are tracked."""

    __tablename__ = "league_seasons"

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
        doc="UTC timestamp when the season ended, or NULL if still active",
    )

    matches = relationship(
        "LeagueMatch",
        back_populates="season",
        doc="Matches logged during this season",
    )
