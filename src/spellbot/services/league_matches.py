from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from asgiref.sync import sync_to_async

from spellbot.database import DatabaseSession
from spellbot.models import LeagueDeck, LeagueMatch, LeagueMatchPlayer, LeagueSeason


class LeagueMatchesService:
    """Manages league match creation, confirmation, and queries."""

    @sync_to_async()
    def create(
        self,
        guild_xid: int,
        season_id: int,
        player_xids: list[int],
        deck_ids: list[int | None],
        winner_xid: int | None,
        channel_xid: int | None = None,
        message_xid: int | None = None,
        seat_positions: dict[int, int] | None = None,
    ) -> LeagueMatch:
        """Create a new match record with per-player deck snapshots.

        seat_positions: {user_xid: seat_number 1–4} — stored on each
        LeagueMatchPlayer row so the ELO updater can apply seat-bias
        correction at confirmation time.
        """
        match = LeagueMatch(
            guild_xid=guild_xid,
            season_id=season_id,
            winner_xid=winner_xid,
            channel_xid=channel_xid,
            message_xid=message_xid,
        )
        DatabaseSession.add(match)
        DatabaseSession.flush()

        for user_xid, deck_id in zip(player_xids, deck_ids, strict=False):
            seat = seat_positions.get(user_xid) if seat_positions else None
            player = LeagueMatchPlayer(
                match_id=match.id,
                user_xid=user_xid,
                deck_id=deck_id,
                confirmed=False,
                seat=seat,
            )
            DatabaseSession.add(player)

        DatabaseSession.commit()
        return match

    @sync_to_async()
    def get_by_id(self, match_id: int) -> LeagueMatch | None:
        return DatabaseSession.get(LeagueMatch, match_id)

    @sync_to_async()
    def confirm_player(
        self, match: LeagueMatch, user_xid: int
    ) -> tuple[bool, bool]:
        """
        Mark one player as confirmed.

        Returns (was_already_confirmed, all_now_confirmed).
        """
        player = next(
            (p for p in match.players if p.user_xid == user_xid), None
        )
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
    def set_dispute_thread(self, match: LeagueMatch, thread_xid: int) -> None:
        match.dispute_thread_xid = thread_xid
        DatabaseSession.commit()

    @sync_to_async()
    def delete(self, match: LeagueMatch) -> None:
        DatabaseSession.delete(match)
        DatabaseSession.commit()

    @sync_to_async()
    def admin_confirm(self, match: LeagueMatch) -> bool:
        """Confirm all players at once (admin override). Returns False if already confirmed."""
        if match.confirmed_at is not None:
            return False
        for player in match.players:
            player.confirmed = True
        match.confirmed_at = datetime.now(tz=UTC)
        DatabaseSession.commit()
        return True

    @sync_to_async()
    def get_pending(self, guild_xid: int, season_id: int) -> list[LeagueMatch]:
        """Return unconfirmed matches in the given season."""
        return (
            DatabaseSession.query(LeagueMatch)
            .filter(
                LeagueMatch.guild_xid == guild_xid,
                LeagueMatch.season_id == season_id,
                LeagueMatch.confirmed_at.is_(None),
            )
            .order_by(LeagueMatch.created_at.asc())
            .all()
        )

    @sync_to_async()
    def get_disputed(self, guild_xid: int, season_id: int) -> list[LeagueMatch]:
        """Return unconfirmed matches that have a dispute thread."""
        return (
            DatabaseSession.query(LeagueMatch)
            .filter(
                LeagueMatch.guild_xid == guild_xid,
                LeagueMatch.season_id == season_id,
                LeagueMatch.confirmed_at.is_(None),
                LeagueMatch.dispute_thread_xid.isnot(None),
            )
            .order_by(LeagueMatch.created_at.asc())
            .all()
        )

    @sync_to_async()
    def get_for_user(
        self,
        guild_xid: int,
        user_xid: int,
        season_id: int | None = None,
        deck_id: int | None = None,
    ) -> list[LeagueMatch]:
        """Return confirmed matches for a user, optionally filtered by season/deck."""
        query = (
            DatabaseSession.query(LeagueMatch)
            .join(LeagueMatchPlayer, LeagueMatchPlayer.match_id == LeagueMatch.id)
            .filter(
                LeagueMatch.guild_xid == guild_xid,
                LeagueMatchPlayer.user_xid == user_xid,
                LeagueMatch.confirmed_at.isnot(None),
            )
        )
        if season_id is not None:
            query = query.filter(LeagueMatch.season_id == season_id)
        if deck_id is not None:
            query = query.filter(LeagueMatchPlayer.deck_id == deck_id)
        return query.order_by(LeagueMatch.created_at.desc()).all()

    @sync_to_async()
    def get_all_pending(self) -> list[LeagueMatch]:
        """Return all unconfirmed matches across all guilds (used by the reminder task)."""
        return (
            DatabaseSession.query(LeagueMatch)
            .filter(LeagueMatch.confirmed_at.is_(None))
            .order_by(LeagueMatch.created_at.asc())
            .all()
        )

    @sync_to_async()
    def get_leaderboard(
        self, guild_xid: int, season_id: int
    ) -> list[dict[str, Any]]:
        """
        Return per-player standing stats for a season (confirmed matches only).

        Each entry: {user_xid, matches, wins, losses, draws, points}
        Not yet filtered by minimum_games — callers should apply that.
        """
        matches = (
            DatabaseSession.query(LeagueMatch)
            .filter(
                LeagueMatch.guild_xid == guild_xid,
                LeagueMatch.season_id == season_id,
                LeagueMatch.confirmed_at.isnot(None),
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
