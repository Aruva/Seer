from __future__ import annotations

from datetime import UTC, datetime

from asgiref.sync import sync_to_async

from seer.database import DatabaseSession
from seer.models import LeagueSeason


class LeagueSeasonsService:
    """Manages league seasons."""

    @sync_to_async()
    def get_active(self, guild_xid: int) -> LeagueSeason | None:
        """Return the currently active (non-ended) season for a guild."""
        return (
            DatabaseSession.query(LeagueSeason)
            .filter(
                LeagueSeason.guild_xid == guild_xid,
                LeagueSeason.end_date.is_(None),
            )
            .one_or_none()
        )

    @sync_to_async()
    def get_by_name(self, guild_xid: int, name: str) -> LeagueSeason | None:
        """Return a season by name."""
        return (
            DatabaseSession.query(LeagueSeason)
            .filter(
                LeagueSeason.guild_xid == guild_xid,
                LeagueSeason.name == name,
            )
            .one_or_none()
        )

    @sync_to_async()
    def create(self, guild_xid: int, name: str) -> LeagueSeason:
        """Create a new season."""
        season = LeagueSeason(guild_xid=guild_xid, name=name)
        DatabaseSession.add(season)
        DatabaseSession.commit()
        return season

    @sync_to_async()
    def end_active(self, guild_xid: int) -> LeagueSeason | None:
        """End the active season, returning it or None if none was active."""
        season = (
            DatabaseSession.query(LeagueSeason)
            .filter(
                LeagueSeason.guild_xid == guild_xid,
                LeagueSeason.end_date.is_(None),
            )
            .one_or_none()
        )
        if season is None:
            return None
        season.end_date = datetime.now(tz=UTC)
        DatabaseSession.commit()
        return season

    @sync_to_async()
    def count_matches(self, season_id: int) -> int:
        """Count confirmed matches in a season."""
        from seer.models import LeagueMatch

        return (
            DatabaseSession.query(LeagueMatch)
            .filter(
                LeagueMatch.season_id == season_id,
                LeagueMatch.confirmed_at.isnot(None),
            )
            .count()
        )
