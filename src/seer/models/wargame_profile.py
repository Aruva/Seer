from __future__ import annotations

from datetime import UTC, datetime
from functools import partial
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from . import Base, now

if TYPE_CHECKING:
    from . import WargameArmy  # noqa: F401


class WargameProfile(Base):
    """Tracks which army a player is currently using per guild + game system."""

    __tablename__ = "wargame_profiles"

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
    game_system = Column(
        String(64),
        primary_key=True,
        nullable=False,
        doc="Game system slug this profile is for",
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
    current_army_id = Column(
        Integer,
        ForeignKey("wargame_armies.id", ondelete="SET NULL"),
        nullable=True,
        doc="The player's currently selected army for this game system",
    )

    current_army = relationship(
        "WargameArmy",
        doc="The player's currently selected army object",
    )
