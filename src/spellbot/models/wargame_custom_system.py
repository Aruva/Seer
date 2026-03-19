from __future__ import annotations

from datetime import UTC, datetime
from functools import partial

from sqlalchemy import BigInteger, Column, DateTime, Integer, String, UniqueConstraint

from . import Base, now


class WargameCustomSystem(Base):
    """A guild-defined custom game system beyond the built-in known systems."""

    __tablename__ = "wargame_custom_systems"
    __table_args__ = (
        UniqueConstraint("guild_xid", "slug", name="uq_wargame_custom_systems_guild_slug"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    guild_xid = Column(
        BigInteger,
        nullable=False,
        index=True,
        doc="The external Discord guild ID that registered this game system",
    )
    slug = Column(
        String(64),
        nullable=False,
        doc="URL-safe identifier used in commands (e.g. 'bolt-action')",
    )
    display_name = Column(
        String(128),
        nullable=False,
        doc="Human-readable name shown in embeds (e.g. 'Bolt Action')",
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=partial(datetime.now, UTC),
        server_default=now,
    )
