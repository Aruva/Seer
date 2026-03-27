from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from asgiref.sync import sync_to_async

from seer.database import DatabaseSession
from seer.models import WargameMatch, WargameMatchPlayer


class WargameMatchesService:
    """Manages wargame match creation, confirmation, and queries."""

    @sync_to_async()
    def create(
        self,
        guild_xid: int,
        season_id: int,
        player_xids: list[int],
        army_ids: list[int | None],
        winner_xid: int | None,
        channel_xid: int | None = None,
        message_xid: int | None = None,
    ) -> WargameMatch:
        match = WargameMatch(
            guild_xid=guild_xid,
            season_id=season_id,
            winner_xid=winner_xid,
            channel_xid=channel_xid,
            message_xid=message_xid,
        )
        DatabaseSession.add(match)
        DatabaseSession.flush()

        for user_xid, army_id in zip(player_xids, army_ids, strict=False):
            player = WargameMatchPlayer(
                match_id=match.id,
                user_xid=user_xid,
                army_id=army_id,
                confirmed=False,
            )
            DatabaseSession.add(player)

        DatabaseSession.commit()
        return match

    @sync_to_async()
    def get_by_id(self, match_id: int) -> WargameMatch | None:
        return DatabaseSession.get(WargameMatch, match_id)

    @sync_to_async()
    def get_by_message_xid(self, message_xid: int) -> WargameMatch | None:
        return (
            DatabaseSession.query(WargameMatch)
            .filter(WargameMatch.message_xid == message_xid)
            .one_or_none()
        )

    @sync_to_async()
    def confirm_player(
        self, match: WargameMatch, user_xid: int
    ) -> tuple[bool, bool]:
        player = next((p for p in match.players if p.user_xid == user_xid), None)
        if player is None:
            return False, False
        if player.confirmed:
            return True, False
        player.confirmed = True
        all_confirmed = all(p.confirmed for p in match.players)
        if all_confirmed:
            match.confirmed_at = datetime.now(tz=UTC)
        DatabaseSession.commit()
        return False, all_confirmed

    @sync_to_async()
    def set_dispute_thread(self, match: WargameMatch, thread_xid: int) -> None:
        match.dispute_thread_xid = thread_xid
        DatabaseSession.commit()

    @sync_to_async()
    def delete(self, match: WargameMatch) -> None:
        DatabaseSession.delete(match)
        DatabaseSession.commit()

    @sync_to_async()
    def admin_confirm(self, match: WargameMatch) -> bool:
        if match.confirmed_at is not None:
            return False
        for player in match.players:
            player.confirmed = True
        match.confirmed_at = datetime.now(tz=UTC)
        DatabaseSession.commit()
        return True

    @sync_to_async()
    def get_pending(self, guild_xid: int, season_id: int) -> list[WargameMatch]:
        return (
            DatabaseSession.query(WargameMatch)
            .filter(
                WargameMatch.guild_xid == guild_xid,
                WargameMatch.season_id == season_id,
                WargameMatch.confirmed_at.is_(None),
            )
            .order_by(WargameMatch.created_at.asc())
            .all()
        )

    @sync_to_async()
    def get_disputed(self, guild_xid: int, season_id: int) -> list[WargameMatch]:
        return (
            DatabaseSession.query(WargameMatch)
            .filter(
                WargameMatch.guild_xid == guild_xid,
                WargameMatch.season_id == season_id,
                WargameMatch.confirmed_at.is_(None),
                WargameMatch.dispute_thread_xid.isnot(None),
            )
            .order_by(WargameMatch.created_at.asc())
            .all()
        )

    @sync_to_async()
    def get_for_user(
        self,
        guild_xid: int,
        user_xid: int,
        season_id: int | None = None,
        army_id: int | None = None,
    ) -> list[WargameMatch]:
        query = (
            DatabaseSession.query(WargameMatch)
            .join(WargameMatchPlayer, WargameMatchPlayer.match_id == WargameMatch.id)
            .filter(
                WargameMatch.guild_xid == guild_xid,
                WargameMatchPlayer.user_xid == user_xid,
                WargameMatch.confirmed_at.isnot(None),
            )
        )
        if season_id is not None:
            query = query.filter(WargameMatch.season_id == season_id)
        if army_id is not None:
            query = query.filter(WargameMatchPlayer.army_id == army_id)
        return query.order_by(WargameMatch.created_at.desc()).all()

    @sync_to_async()
    def get_leaderboard(
        self, guild_xid: int, season_id: int
    ) -> list[dict[str, Any]]:
        matches = (
            DatabaseSession.query(WargameMatch)
            .filter(
                WargameMatch.guild_xid == guild_xid,
                WargameMatch.season_id == season_id,
                WargameMatch.confirmed_at.isnot(None),
            )
            .all()
        )

        standings: dict[int, dict[str, Any]] = {}
        for match in matches:
            for player in match.players:
                uid = player.user_xid
                if uid not in standings:
                    standings[uid] = {
                        "user_xid": uid,
                        "matches": 0,
                        "wins": 0,
                        "losses": 0,
                        "draws": 0,
                        "points": 0,
                    }
                s = standings[uid]
                s["matches"] += 1
                if match.winner_xid is None:
                    s["draws"] += 1
                elif match.winner_xid == uid:
                    s["wins"] += 1
                else:
                    s["losses"] += 1

        return list(standings.values())


    @sync_to_async()
    def get_all_pending(self) -> list[WargameMatch]:
        """Return all unconfirmed wargame matches across all guilds (for the reminder task)."""
        return (
            DatabaseSession.query(WargameMatch)
            .filter(WargameMatch.confirmed_at.is_(None))
            .all()
        )
