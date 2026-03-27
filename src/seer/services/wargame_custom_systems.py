from __future__ import annotations

from asgiref.sync import sync_to_async

from seer.database import DatabaseSession
from seer.models import WargameCustomSystem


class WargameCustomSystemsService:
    """Manage guild-defined custom wargame game systems."""

    def __init__(self) -> None:
        self.session = DatabaseSession

    @sync_to_async()
    def list_for_guild(self, guild_xid: int) -> list[WargameCustomSystem]:
        """Return all custom game systems registered for this guild."""
        return (
            self.session.query(WargameCustomSystem)
            .filter_by(guild_xid=guild_xid)
            .order_by(WargameCustomSystem.display_name)
            .all()
        )

    @sync_to_async()
    def get_by_slug(self, guild_xid: int, slug: str) -> WargameCustomSystem | None:
        """Return a custom game system by its slug, or None if not found."""
        return (
            self.session.query(WargameCustomSystem)
            .filter_by(guild_xid=guild_xid, slug=slug)
            .first()
        )

    @sync_to_async()
    def create(self, guild_xid: int, slug: str, display_name: str) -> WargameCustomSystem:
        """Register a new custom game system for this guild."""
        system = WargameCustomSystem(
            guild_xid=guild_xid,
            slug=slug,
            display_name=display_name,
        )
        self.session.add(system)
        self.session.flush()
        return system

    @sync_to_async()
    def delete(self, system: WargameCustomSystem) -> None:
        """Remove a custom game system."""
        self.session.delete(system)
        self.session.flush()

    @sync_to_async()
    def count(self, guild_xid: int) -> int:
        """Count the number of custom game systems for this guild."""
        return (
            self.session.query(WargameCustomSystem)
            .filter_by(guild_xid=guild_xid)
            .count()
        )
