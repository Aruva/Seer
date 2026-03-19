from __future__ import annotations

from asgiref.sync import sync_to_async

from spellbot.database import DatabaseSession
from spellbot.models import LeagueDeck, LeagueProfile


class LeagueDecksService:
    """Manages player decks."""

    @sync_to_async()
    def get_profile(self, guild_xid: int, user_xid: int) -> LeagueProfile:
        """Fetch (or create) a player's league profile."""
        profile = (
            DatabaseSession.query(LeagueProfile)
            .filter(
                LeagueProfile.guild_xid == guild_xid,
                LeagueProfile.user_xid == user_xid,
            )
            .one_or_none()
        )
        if profile is None:
            profile = LeagueProfile(guild_xid=guild_xid, user_xid=user_xid)
            DatabaseSession.add(profile)
            DatabaseSession.commit()
        return profile

    @sync_to_async()
    def count(self, guild_xid: int, user_xid: int) -> int:
        """Count how many decks the player currently has."""
        return (
            DatabaseSession.query(LeagueDeck)
            .filter(
                LeagueDeck.guild_xid == guild_xid,
                LeagueDeck.user_xid == user_xid,
            )
            .count()
        )

    @sync_to_async()
    def get_by_name(
        self, guild_xid: int, user_xid: int, name: str
    ) -> LeagueDeck | None:
        return (
            DatabaseSession.query(LeagueDeck)
            .filter(
                LeagueDeck.guild_xid == guild_xid,
                LeagueDeck.user_xid == user_xid,
                LeagueDeck.name == name,
            )
            .one_or_none()
        )

    @sync_to_async()
    def get_by_id(self, deck_id: int) -> LeagueDeck | None:
        return DatabaseSession.get(LeagueDeck, deck_id)

    @sync_to_async()
    def list_all(self, guild_xid: int, user_xid: int) -> list[LeagueDeck]:
        return (
            DatabaseSession.query(LeagueDeck)
            .filter(
                LeagueDeck.guild_xid == guild_xid,
                LeagueDeck.user_xid == user_xid,
            )
            .order_by(LeagueDeck.created_at.desc())
            .all()
        )

    @sync_to_async()
    def create(
        self,
        guild_xid: int,
        user_xid: int,
        name: str,
        deck_list: str | None,
        set_as_current: bool = True,
    ) -> LeagueDeck:
        deck = LeagueDeck(
            guild_xid=guild_xid,
            user_xid=user_xid,
            name=name,
            deck_list=deck_list,
        )
        DatabaseSession.add(deck)
        DatabaseSession.flush()  # get the id
        if set_as_current:
            profile = (
                DatabaseSession.query(LeagueProfile)
                .filter(
                    LeagueProfile.guild_xid == guild_xid,
                    LeagueProfile.user_xid == user_xid,
                )
                .one_or_none()
            )
            if profile is None:
                profile = LeagueProfile(
                    guild_xid=guild_xid,
                    user_xid=user_xid,
                    current_deck_id=deck.id,
                )
                DatabaseSession.add(profile)
            else:
                profile.current_deck_id = deck.id
        DatabaseSession.commit()
        return deck

    @sync_to_async()
    def rename(self, deck: LeagueDeck, new_name: str) -> None:
        deck.name = new_name
        DatabaseSession.commit()

    @sync_to_async()
    def set_deck_list(self, deck: LeagueDeck, deck_list: str) -> None:
        deck.deck_list = deck_list
        DatabaseSession.commit()

    @sync_to_async()
    def set_current(self, guild_xid: int, user_xid: int, deck: LeagueDeck) -> None:
        profile = (
            DatabaseSession.query(LeagueProfile)
            .filter(
                LeagueProfile.guild_xid == guild_xid,
                LeagueProfile.user_xid == user_xid,
            )
            .one_or_none()
        )
        if profile is None:
            profile = LeagueProfile(
                guild_xid=guild_xid,
                user_xid=user_xid,
                current_deck_id=deck.id,
            )
            DatabaseSession.add(profile)
        else:
            profile.current_deck_id = deck.id
        DatabaseSession.commit()

    @sync_to_async()
    def delete(self, guild_xid: int, user_xid: int, deck: LeagueDeck) -> None:
        """Delete a deck and clear it from the player's profile if it was current."""
        from spellbot.models import LeagueMatchPlayer

        # Remove deck references from match players
        DatabaseSession.query(LeagueMatchPlayer).filter(
            LeagueMatchPlayer.deck_id == deck.id
        ).update({LeagueMatchPlayer.deck_id: None})

        # Clear from profile if it's the current deck
        profile = (
            DatabaseSession.query(LeagueProfile)
            .filter(
                LeagueProfile.guild_xid == guild_xid,
                LeagueProfile.user_xid == user_xid,
            )
            .one_or_none()
        )
        if profile and profile.current_deck_id == deck.id:
            profile.current_deck_id = None

        DatabaseSession.delete(deck)
        DatabaseSession.commit()

    @sync_to_async()
    def get_deck_stats(
        self, guild_xid: int, user_xid: int, deck_id: int
    ) -> dict[str, int]:
        """Return win/loss/draw counts for a deck (confirmed matches only)."""
        from spellbot.models import LeagueMatch, LeagueMatchPlayer

        rows = (
            DatabaseSession.query(LeagueMatch)
            .join(
                LeagueMatchPlayer,
                LeagueMatchPlayer.match_id == LeagueMatch.id,
            )
            .filter(
                LeagueMatch.guild_xid == guild_xid,
                LeagueMatchPlayer.user_xid == user_xid,
                LeagueMatchPlayer.deck_id == deck_id,
                LeagueMatch.confirmed_at.isnot(None),
            )
            .all()
        )
        wins = sum(1 for m in rows if m.winner_xid == user_xid)
        draws = sum(1 for m in rows if m.winner_xid is None)
        losses = len(rows) - wins - draws
        return {"total": len(rows), "wins": wins, "draws": draws, "losses": losses}
