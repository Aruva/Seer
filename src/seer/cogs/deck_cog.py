from __future__ import annotations

import logging
from urllib.parse import urlparse
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from seer.database import db_session_manager
from seer.models import VALID_DECK_LIST_HOSTS
from seer.settings import settings
from seer.utils import for_all_callbacks, is_guild

if TYPE_CHECKING:
    from seer import Seer

logger = logging.getLogger(__name__)


def _validate_deck_list(url: str) -> bool:
    try:
        hostname = urlparse(url).hostname or ""
        hostname = hostname.lower().removeprefix("www.")
        return hostname in VALID_DECK_LIST_HOSTS
    except Exception:
        return False


@for_all_callbacks(app_commands.check(is_guild))
class DeckCog(commands.Cog):
    def __init__(self, bot: Seer) -> None:
        self.bot = bot

    deck_group = app_commands.Group(name="deck", description="Manage your EDH decks.")

    # ── /deck create ──────────────────────────────────────────────────────────

    @deck_group.command(name="create", description="Register a new deck.")
    @app_commands.describe(
        name="Name for your deck (max 64 characters).",
        deck_list="Optional URL to your deck list (Moxfield, Archidekt, etc.).",
    )
    async def create(
        self,
        interaction: discord.Interaction,
        name: str,
        deck_list: str | None = None,
    ) -> None:
        async with db_session_manager():
            await self._handle_create(interaction, name, deck_list)

    # ── /deck list ────────────────────────────────────────────────────────────

    @deck_group.command(name="list", description="Show all your registered decks.")
    async def list_decks(self, interaction: discord.Interaction) -> None:
        async with db_session_manager():
            await self._handle_list(interaction)

    # ── /deck use ─────────────────────────────────────────────────────────────

    @deck_group.command(name="use", description="Set a deck as your active deck.")
    @app_commands.describe(name="Name of the deck to activate.")
    async def use(self, interaction: discord.Interaction, name: str) -> None:
        async with db_session_manager():
            await self._handle_use(interaction, name)

    # ── /deck delete ──────────────────────────────────────────────────────────

    @deck_group.command(name="delete", description="Delete one of your decks.")
    @app_commands.describe(name="Name of the deck to delete.")
    async def delete(self, interaction: discord.Interaction, name: str) -> None:
        async with db_session_manager():
            await self._handle_delete(interaction, name)

    # ── /deck rename ──────────────────────────────────────────────────────────

    @deck_group.command(name="rename", description="Rename one of your decks.")
    @app_commands.describe(name="Current deck name.", new_name="New deck name.")
    async def rename(
        self, interaction: discord.Interaction, name: str, new_name: str
    ) -> None:
        async with db_session_manager():
            await self._handle_rename(interaction, name, new_name)

    # ── /deck set-list ────────────────────────────────────────────────────────

    @deck_group.command(name="set-list", description="Update the deck list URL for a deck.")
    @app_commands.describe(name="Deck name.", deck_list="New deck list URL.")
    async def set_list(
        self, interaction: discord.Interaction, name: str, deck_list: str
    ) -> None:
        async with db_session_manager():
            await self._handle_set_list(interaction, name, deck_list)

    # ── /deck stats ───────────────────────────────────────────────────────────

    @deck_group.command(name="stats", description="View win/loss stats for a deck.")
    @app_commands.describe(name="Deck name (leave blank for your active deck).")
    async def stats(
        self, interaction: discord.Interaction, name: str | None = None
    ) -> None:
        async with db_session_manager():
            await self._handle_stats(interaction, name)

    # ── implementations ───────────────────────────────────────────────────────

    async def _handle_create(
        self, interaction: discord.Interaction, name: str, deck_list: str | None
    ) -> None:
        assert interaction.guild is not None
        from seer.services import LeagueConfigService, LeagueDecksService

        if len(name) > 64:
            await interaction.response.send_message(
                "Deck name must be 64 characters or fewer.", ephemeral=True
            )
            return

        if deck_list and not _validate_deck_list(deck_list):
            valid = ", ".join(f"`{h}`" for h in VALID_DECK_LIST_HOSTS)
            await interaction.response.send_message(
                f"The deck list URL must be from one of: {valid}.", ephemeral=True
            )
            return

        cfg_svc = LeagueConfigService()
        config = await cfg_svc.upsert(interaction.guild.id)
        decks_svc = LeagueDecksService()
        count = await decks_svc.count(interaction.guild.id, interaction.user.id)

        if count >= config.deck_limit:
            await interaction.response.send_message(
                f"You have reached the deck limit of {config.deck_limit}.", ephemeral=True
            )
            return

        existing = await decks_svc.get_by_name(interaction.guild.id, interaction.user.id, name)
        if existing:
            await interaction.response.send_message(
                f'You already have a deck named "{name}".', ephemeral=True
            )
            return

        await decks_svc.create(
            interaction.guild.id, interaction.user.id, name, deck_list, set_as_current=True
        )
        await interaction.response.send_message(
            f'✅ Deck **{name}** created and set as your active deck.', ephemeral=True
        )

    async def _handle_list(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None
        from seer.services import LeagueDecksService

        decks_svc = LeagueDecksService()
        decks = await decks_svc.list_all(interaction.guild.id, interaction.user.id)

        if not decks:
            await interaction.response.send_message(
                "You have no registered decks. Use `/deck create` to add one.", ephemeral=True
            )
            return

        # Fetch current deck to mark it
        profile = await decks_svc.get_profile(interaction.guild.id, interaction.user.id)
        current_id = profile.current_deck_id

        lines = []
        for deck in decks:
            marker = "▶ " if deck.id == current_id else "  "
            if deck.deck_list:
                lines.append(f"{marker}[{deck.name}]({deck.deck_list})")
            else:
                lines.append(f"{marker}{deck.name}")

        embed = discord.Embed(
            title="Your Decks",
            description="\n".join(lines),
            color=discord.Color.blue(),
        )
        embed.set_footer(text="▶ = currently active deck")
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _handle_use(self, interaction: discord.Interaction, name: str) -> None:
        assert interaction.guild is not None
        from seer.services import LeagueDecksService

        decks_svc = LeagueDecksService()
        deck = await decks_svc.get_by_name(interaction.guild.id, interaction.user.id, name)
        if deck is None:
            await interaction.response.send_message(
                f'You have no deck named "{name}".', ephemeral=True
            )
            return

        await decks_svc.set_current(interaction.guild.id, interaction.user.id, deck)
        await interaction.response.send_message(
            f'✅ **{name}** is now your active deck.', ephemeral=True
        )

    async def _handle_delete(self, interaction: discord.Interaction, name: str) -> None:
        assert interaction.guild is not None
        from seer.services import LeagueDecksService

        decks_svc = LeagueDecksService()
        deck = await decks_svc.get_by_name(interaction.guild.id, interaction.user.id, name)
        if deck is None:
            await interaction.response.send_message(
                f'You have no deck named "{name}".', ephemeral=True
            )
            return

        await decks_svc.delete(interaction.guild.id, interaction.user.id, deck)
        await interaction.response.send_message(
            f'🗑️ Deck **{name}** has been deleted.', ephemeral=True
        )

    async def _handle_rename(
        self, interaction: discord.Interaction, name: str, new_name: str
    ) -> None:
        assert interaction.guild is not None
        from seer.services import LeagueDecksService

        if len(new_name) > 64:
            await interaction.response.send_message(
                "New name must be 64 characters or fewer.", ephemeral=True
            )
            return

        decks_svc = LeagueDecksService()
        deck = await decks_svc.get_by_name(interaction.guild.id, interaction.user.id, name)
        if deck is None:
            await interaction.response.send_message(
                f'You have no deck named "{name}".', ephemeral=True
            )
            return

        conflict = await decks_svc.get_by_name(interaction.guild.id, interaction.user.id, new_name)
        if conflict:
            await interaction.response.send_message(
                f'You already have a deck named "{new_name}".', ephemeral=True
            )
            return

        await decks_svc.rename(deck, new_name)
        await interaction.response.send_message(
            f'✅ Deck renamed from **{name}** to **{new_name}**.', ephemeral=True
        )

    async def _handle_set_list(
        self, interaction: discord.Interaction, name: str, deck_list: str
    ) -> None:
        assert interaction.guild is not None
        from seer.services import LeagueDecksService

        if not _validate_deck_list(deck_list):
            valid = ", ".join(f"`{h}`" for h in VALID_DECK_LIST_HOSTS)
            await interaction.response.send_message(
                f"The deck list URL must be from one of: {valid}.", ephemeral=True
            )
            return

        decks_svc = LeagueDecksService()
        deck = await decks_svc.get_by_name(interaction.guild.id, interaction.user.id, name)
        if deck is None:
            await interaction.response.send_message(
                f'You have no deck named "{name}".', ephemeral=True
            )
            return

        await decks_svc.set_deck_list(deck, deck_list)
        await interaction.response.send_message(
            f'✅ Deck list updated for **{name}**.', ephemeral=True
        )

    async def _handle_stats(
        self, interaction: discord.Interaction, name: str | None
    ) -> None:
        assert interaction.guild is not None
        from seer.services import LeagueDecksService, LeagueSeasonsService

        decks_svc = LeagueDecksService()

        if name is None:
            profile = await decks_svc.get_profile(interaction.guild.id, interaction.user.id)
            if not profile.current_deck_id:
                await interaction.response.send_message(
                    "You have no active deck. Use `/deck use` to select one.", ephemeral=True
                )
                return
            deck = await decks_svc.get_by_id(profile.current_deck_id)
        else:
            deck = await decks_svc.get_by_name(interaction.guild.id, interaction.user.id, name)

        if deck is None:
            await interaction.response.send_message(
                f'No deck named "{name}" found.' if name else "Deck not found.", ephemeral=True
            )
            return

        all_stats = await decks_svc.get_deck_stats(
            interaction.guild.id, interaction.user.id, deck.id
        )

        deck_label = f"[{deck.name}]({deck.deck_list})" if deck.deck_list else deck.name
        embed = discord.Embed(
            title=f"Deck Stats — {deck.name}",
            description=f"Overall statistics for {deck_label}.",
            color=discord.Color.blue(),
        )
        if deck.deck_list:
            embed.url = deck.deck_list
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        total = all_stats["total"]
        wins = all_stats["wins"]
        draws = all_stats["draws"]
        losses = all_stats["losses"]
        win_rate = round(wins / total * 100) if total else 0

        embed.add_field(name="Matches", value=f"{total} game{'s' if total != 1 else ''}")
        embed.add_field(name="Wins", value=str(wins))
        embed.add_field(name="Draws", value=str(draws))
        embed.add_field(name="Losses", value=str(losses))
        embed.add_field(name="Win Rate", value=f"{win_rate}%")

        # Season breakdown
        seasons_svc = LeagueSeasonsService()
        active = await seasons_svc.get_active(interaction.guild.id)
        if active:
            from seer.services import LeagueMatchesService
            matches_svc = LeagueMatchesService()
            season_matches = await matches_svc.get_for_user(
                interaction.guild.id,
                interaction.user.id,
                season_id=active.id,
                deck_id=deck.id,
            )
            sw = sum(1 for m in season_matches if m.winner_xid == interaction.user.id)
            sd = sum(1 for m in season_matches if m.winner_xid is None)
            sl = len(season_matches) - sw - sd
            sr = round(sw / len(season_matches) * 100) if season_matches else 0
            embed.add_field(
                name=f"This Season ({active.name})",
                value=f"{len(season_matches)} games · {sw}W {sd}D {sl}L · {sr}% win rate",
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: Seer) -> None:  # pragma: no cover
    await bot.add_cog(DeckCog(bot), guild=settings.GUILD_OBJECT)
