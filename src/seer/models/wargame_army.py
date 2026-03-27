from __future__ import annotations

from datetime import UTC, datetime
from functools import partial

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String

from . import Base, now

# Well-known game system slugs. Admins may also use any free-form string.
KNOWN_GAME_SYSTEMS: dict[str, str] = {
    "warmachine": "Warmachine/Hordes",
    "warhammer40k": "Warhammer 40,000",
}

# Known Magic: The Gathering 60-card 1v1 formats.
# These use the same underlying wargame infrastructure but are surfaced
# through dedicated /m* commands rather than /w* commands.
KNOWN_MAGIC_FORMATS: dict[str, str] = {
    "standard": "Standard",
    "pioneer": "Pioneer",
    "modern": "Modern",
    "legacy": "Legacy",
    "vintage": "Vintage",
}


class WargameArmy(Base):
    """An army list registered by a player for wargame league play."""

    __tablename__ = "wargame_armies"

    id = Column(
        Integer,
        autoincrement=True,
        primary_key=True,
        nullable=False,
        doc="Internal army ID",
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
        doc="Discord guild this army belongs to",
    )
    user_xid = Column(
        BigInteger,
        ForeignKey("users.xid", ondelete="CASCADE"),
        index=True,
        nullable=False,
        doc="Discord user ID of the army owner",
    )
    game_system = Column(
        String(64),
        nullable=False,
        index=True,
        doc="Game system slug (e.g. 'warmachine', 'warhammer40k', or custom)",
    )
    name = Column(
        String(64),
        nullable=False,
        doc="Display name for this army",
    )
    faction = Column(
        String(64),
        nullable=True,
        doc="Faction or sub-faction (e.g. Cygnar, Space Marines)",
    )
    list_url = Column(
        String(512),
        nullable=True,
        doc="Optional URL to the army list (Battlescribe, New Recruit, etc.)",
    )
