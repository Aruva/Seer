from __future__ import annotations

from datetime import UTC, datetime

from asgiref.sync import sync_to_async

from seer.database import DatabaseSession
from seer.models import WargameSeason


class WargameSeasonsService:
    """Manages wargame seasons per game system."""

    @sync_to_async()
    def get_active(self, guild_xid: int, game_system: str) -> WargameSeason | None:
        return (
            DatabaseSession.query(WargameSeason)
            .filter(
                WargameSeason.guild_xid == guild_xid,
                WargameSeason.game_system == game_system,
                WargameSeason.end_date.is_(None),
            )
            .one_or_none()
        )

    @sync_to_async()
    def get_by_name(
        self, guild_xid: int, game_system: str, name: str
    ) -> WargameSeason | None:
        return (
            DatabaseSession.query(WargameSeason)
            .filter(
                WargameSeason.guild_xid == guild_xid,
                WargameSeason.game_system == game_system,
                WargameSeason.name == name,
            )
            .one_or_none()
        )

    @sync_to_async()
    def create(self, guild_xid: int, game_system: str, name: str) -> WargameSeason:
        season = WargameSeason(guild_xid=guild_xid, game_system=game_system, name=name)
        DatabaseSession.add(season)
        DatabaseSession.commit()
        return season

    @sync_to_async()
    def end_active(self, guild_xid: int, game_system: str) -> WargameSeason | None:
        season = (
            DatabaseSession.query(WargameSeason)
            .filter(
                WargameSeason.guild_xid == guild_xid,
                WargameSeason.game_system == game_system,
                WargameSeason.end_date.is_(None),
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
        from seer.models import WargameMatch

        return (
            DatabaseSession.query(WargameMatch)
            .filter(
                WargameMatch.season_id == season_id,
                WargameMatch.confirmed_at.isnot(None),
            )
            .count()
        )
