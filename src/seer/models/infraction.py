from __future__ import annotations

from datetime import UTC, datetime
from functools import partial
from typing import TYPE_CHECKING, TypedDict

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, Text

from . import Base, now

if TYPE_CHECKING:
    from . import Guild, User  # noqa: F401


class InfractionDict(TypedDict):
    id: int
    guild_xid: int
    user_xid: int
    judge_xid: int | None
    judge_name: str | None
    game_system: str
    infraction: str
    infraction_category: str
    penalty: str
    round: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class Infraction(Base):
    """Records of player infractions issued by judges."""

    __tablename__ = "infractions"

    id = Column(
        Integer,
        autoincrement=True,
        nullable=False,
        primary_key=True,
        doc="A pk for this infraction",
    )
    guild_xid = Column(
        BigInteger,
        ForeignKey("guilds.xid", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="The Discord guild where this infraction was issued",
    )
    user_xid = Column(
        BigInteger,
        ForeignKey("users.xid", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="The Discord user who received the infraction",
    )
    judge_xid = Column(
        BigInteger,
        nullable=True,
        doc="The Discord user ID of the judge who issued the infraction",
    )
    judge_name = Column(
        String(100),
        nullable=True,
        doc="The name of the judge who issued the infraction",
    )
    game_system = Column(
        String(50),
        nullable=False,
        doc="The game system (e.g. MTG, Warmachine, Warhammer, Redemption)",
    )
    infraction = Column(
        String(200),
        nullable=False,
        doc="The infraction type (e.g. Slow Play, Deck Error)",
    )
    infraction_category = Column(
        String(100),
        nullable=False,
        doc="The infraction category (e.g. Tournament Errors, Game Play Errors)",
    )
    penalty = Column(
        String(50),
        nullable=False,
        doc="The penalty level (warning, game_loss, match_loss, dq)",
    )
    round = Column(
        String(10),
        nullable=True,
        doc="The round number when the infraction occurred",
    )
    notes = Column(
        Text,
        nullable=True,
        doc="Additional notes about the infraction",
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=partial(datetime.now, UTC),
        server_default=now,
        doc="UTC timestamp when this infraction was created",
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=partial(datetime.now, UTC),
        server_default=now,
        onupdate=partial(datetime.now, UTC),
        doc="UTC timestamp when this infraction was last updated",
    )

    def to_dict(self) -> InfractionDict:
        return {
            "id": self.id,
            "guild_xid": self.guild_xid,
            "user_xid": self.user_xid,
            "judge_xid": self.judge_xid,
            "judge_name": self.judge_name,
            "game_system": self.game_system,
            "infraction": self.infraction,
            "infraction_category": self.infraction_category,
            "penalty": self.penalty,
            "round": self.round,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
