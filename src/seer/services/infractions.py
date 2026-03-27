from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from asgiref.sync import sync_to_async

from seer.database import DatabaseSession
from seer.models import Infraction, InfractionDict, User


class InfractionsService:
    @sync_to_async()
    def create(
        self,
        *,
        guild_xid: int,
        user_xid: int,
        judge_xid: int | None = None,
        judge_name: str | None = None,
        game_system: str,
        infraction: str,
        infraction_category: str,
        penalty: str,
        round: str | None = None,
        notes: str | None = None,
    ) -> InfractionDict:
        row = Infraction(
            guild_xid=guild_xid,
            user_xid=user_xid,
            judge_xid=judge_xid,
            judge_name=judge_name,
            game_system=game_system,
            infraction=infraction,
            infraction_category=infraction_category,
            penalty=penalty,
            round=round,
            notes=notes,
        )
        DatabaseSession.add(row)
        DatabaseSession.commit()
        DatabaseSession.refresh(row)
        return row.to_dict()

    @sync_to_async()
    def get_by_user(
        self,
        *,
        guild_xid: int,
        user_xid: int,
    ) -> list[InfractionDict]:
        rows = (
            DatabaseSession.query(Infraction)
            .filter(
                Infraction.guild_xid == guild_xid,
                Infraction.user_xid == user_xid,
            )
            .order_by(Infraction.created_at.desc())
            .all()
        )
        return [r.to_dict() for r in rows]

    @sync_to_async()
    def get_by_guild(
        self,
        *,
        guild_xid: int,
        limit: int = 50,
        offset: int = 0,
    ) -> list[InfractionDict]:
        rows = (
            DatabaseSession.query(Infraction)
            .filter(Infraction.guild_xid == guild_xid)
            .order_by(Infraction.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [r.to_dict() for r in rows]

    @sync_to_async()
    def search_players(
        self,
        *,
        guild_xid: int,
        query: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search for players in a guild by name (partial match)."""
        users = (
            DatabaseSession.query(User)
            .filter(User.name.ilike(f"%{query}%"))
            .order_by(User.name)
            .limit(limit)
            .all()
        )
        results = []
        for user in users:
            infraction_count = (
                DatabaseSession.query(Infraction)
                .filter(
                    Infraction.guild_xid == guild_xid,
                    Infraction.user_xid == user.xid,
                )
                .count()
            )
            results.append({
                "xid": user.xid,
                "name": user.name,
                "infraction_count": infraction_count,
            })
        return results

    @sync_to_async()
    def get_player_summary(
        self,
        *,
        guild_xid: int,
        user_xid: int,
    ) -> dict[str, Any] | None:
        """Get a player summary with infraction history."""
        user = DatabaseSession.query(User).filter(User.xid == user_xid).one_or_none()
        if not user:
            return None
        infractions = (
            DatabaseSession.query(Infraction)
            .filter(
                Infraction.guild_xid == guild_xid,
                Infraction.user_xid == user_xid,
            )
            .order_by(Infraction.created_at.desc())
            .all()
        )
        return {
            "xid": user.xid,
            "name": user.name,
            "banned": user.banned,
            "infractions": [i.to_dict() for i in infractions],
            "total_infractions": len(infractions),
            "warnings": sum(1 for i in infractions if i.penalty == "warning"),
            "game_losses": sum(1 for i in infractions if i.penalty == "game_loss"),
            "match_losses": sum(1 for i in infractions if i.penalty == "match_loss"),
            "dqs": sum(1 for i in infractions if i.penalty == "dq"),
        }
