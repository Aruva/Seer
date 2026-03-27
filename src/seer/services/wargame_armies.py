from __future__ import annotations

from asgiref.sync import sync_to_async

from seer.database import DatabaseSession
from seer.models import WargameArmy, WargameProfile


class WargameArmiesService:
    """Manages player armies and profiles for wargame tracking."""

    @sync_to_async()
    def get_profile(
        self, guild_xid: int, user_xid: int, game_system: str
    ) -> WargameProfile:
        profile = (
            DatabaseSession.query(WargameProfile)
            .filter(
                WargameProfile.guild_xid == guild_xid,
                WargameProfile.user_xid == user_xid,
                WargameProfile.game_system == game_system,
            )
            .one_or_none()
        )
        if profile is None:
            profile = WargameProfile(
                guild_xid=guild_xid,
                user_xid=user_xid,
                game_system=game_system,
            )
            DatabaseSession.add(profile)
            DatabaseSession.commit()
        return profile

    @sync_to_async()
    def count(self, guild_xid: int, user_xid: int, game_system: str) -> int:
        return (
            DatabaseSession.query(WargameArmy)
            .filter(
                WargameArmy.guild_xid == guild_xid,
                WargameArmy.user_xid == user_xid,
                WargameArmy.game_system == game_system,
            )
            .count()
        )

    @sync_to_async()
    def get_by_name(
        self, guild_xid: int, user_xid: int, game_system: str, name: str
    ) -> WargameArmy | None:
        return (
            DatabaseSession.query(WargameArmy)
            .filter(
                WargameArmy.guild_xid == guild_xid,
                WargameArmy.user_xid == user_xid,
                WargameArmy.game_system == game_system,
                WargameArmy.name == name,
            )
            .one_or_none()
        )

    @sync_to_async()
    def get_by_id(self, army_id: int) -> WargameArmy | None:
        return DatabaseSession.get(WargameArmy, army_id)

    @sync_to_async()
    def list_all(
        self, guild_xid: int, user_xid: int, game_system: str
    ) -> list[WargameArmy]:
        return (
            DatabaseSession.query(WargameArmy)
            .filter(
                WargameArmy.guild_xid == guild_xid,
                WargameArmy.user_xid == user_xid,
                WargameArmy.game_system == game_system,
            )
            .order_by(WargameArmy.created_at.desc())
            .all()
        )

    @sync_to_async()
    def create(
        self,
        guild_xid: int,
        user_xid: int,
        game_system: str,
        name: str,
        faction: str | None,
        list_url: str | None,
        set_as_current: bool = True,
    ) -> WargameArmy:
        army = WargameArmy(
            guild_xid=guild_xid,
            user_xid=user_xid,
            game_system=game_system,
            name=name,
            faction=faction,
            list_url=list_url,
        )
        DatabaseSession.add(army)
        DatabaseSession.flush()

        if set_as_current:
            profile = (
                DatabaseSession.query(WargameProfile)
                .filter(
                    WargameProfile.guild_xid == guild_xid,
                    WargameProfile.user_xid == user_xid,
                    WargameProfile.game_system == game_system,
                )
                .one_or_none()
            )
            if profile is None:
                profile = WargameProfile(
                    guild_xid=guild_xid,
                    user_xid=user_xid,
                    game_system=game_system,
                    current_army_id=army.id,
                )
                DatabaseSession.add(profile)
            else:
                profile.current_army_id = army.id

        DatabaseSession.commit()
        return army

    @sync_to_async()
    def rename(self, army: WargameArmy, new_name: str) -> None:
        army.name = new_name
        DatabaseSession.commit()

    @sync_to_async()
    def set_faction(self, army: WargameArmy, faction: str) -> None:
        army.faction = faction
        DatabaseSession.commit()

    @sync_to_async()
    def set_list_url(self, army: WargameArmy, list_url: str) -> None:
        army.list_url = list_url
        DatabaseSession.commit()

    @sync_to_async()
    def set_current(
        self, guild_xid: int, user_xid: int, game_system: str, army: WargameArmy
    ) -> None:
        profile = (
            DatabaseSession.query(WargameProfile)
            .filter(
                WargameProfile.guild_xid == guild_xid,
                WargameProfile.user_xid == user_xid,
                WargameProfile.game_system == game_system,
            )
            .one_or_none()
        )
        if profile is None:
            profile = WargameProfile(
                guild_xid=guild_xid,
                user_xid=user_xid,
                game_system=game_system,
                current_army_id=army.id,
            )
            DatabaseSession.add(profile)
        else:
            profile.current_army_id = army.id
        DatabaseSession.commit()

    @sync_to_async()
    def delete(
        self, guild_xid: int, user_xid: int, game_system: str, army: WargameArmy
    ) -> None:
        from seer.models import WargameMatchPlayer

        DatabaseSession.query(WargameMatchPlayer).filter(
            WargameMatchPlayer.army_id == army.id
        ).update({WargameMatchPlayer.army_id: None})

        profile = (
            DatabaseSession.query(WargameProfile)
            .filter(
                WargameProfile.guild_xid == guild_xid,
                WargameProfile.user_xid == user_xid,
                WargameProfile.game_system == game_system,
            )
            .one_or_none()
        )
        if profile and profile.current_army_id == army.id:
            profile.current_army_id = None

        DatabaseSession.delete(army)
        DatabaseSession.commit()

    @sync_to_async()
    def get_army_stats(
        self, guild_xid: int, user_xid: int, army_id: int
    ) -> dict[str, int]:
        from seer.models import WargameMatch, WargameMatchPlayer

        rows = (
            DatabaseSession.query(WargameMatch)
            .join(WargameMatchPlayer, WargameMatchPlayer.match_id == WargameMatch.id)
            .filter(
                WargameMatch.guild_xid == guild_xid,
                WargameMatchPlayer.user_xid == user_xid,
                WargameMatchPlayer.army_id == army_id,
                WargameMatch.confirmed_at.isnot(None),
            )
            .all()
        )
        wins = sum(1 for m in rows if m.winner_xid == user_xid)
        draws = sum(1 for m in rows if m.winner_xid is None)
        losses = len(rows) - wins - draws
        return {"total": len(rows), "wins": wins, "draws": draws, "losses": losses}
