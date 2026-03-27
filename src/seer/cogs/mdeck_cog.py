from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from seer.database import db_session_manager
from seer.settings import settings
from seer.utils import for_all_callbacks, is_guild

from ._magic_helpers import (
    VALID_DECK_LIST_HOSTS,
    display_format,
    magic_format_autocomplete,
    normalize_format,
    validate_deck_url,
)

if TYPE_CHECKING:
    from seer import Seer

logger = logging.getLogger(__name__)


@for_all_callbacks(app_commands.check(is_guild))
class MDeckCog(commands.Cog):
    def __init__(self, bot: Seer) -> None:
        self.bot = bot

    mdeck_group = app_commands.Group(
        name="mdeck",
        description="Manage your Magic: The Gathering decks.",
    )

    # ── /mdeck create ─────────────────────────────────────────────────────────

    @mdeck_group.command(name="create", description="Register a new deck.")
    @app_commands.describe(
        format="The Magic format this deck is built for.",
        name="Deck name or archetype (e.g. 'Temur Rhinos', 'UW Control').",
        archetype="Optional sub-archetype or variant label.",
        list_url="Optional link to your deck list (Moxfield, Archidekt, etc.).",
    )
    @app_commands.autocomplete(format=magic_format_autocomplete)
    async def create(
        self,
        interaction: discord.Interaction,
        format: str,
        name: str,
        archetype: str | None = None,
        list_url: str | None = None,
    ) -> None:
        async with db_session_manager():
            await self._handle_create(
                interaction, normalize_format(format), name, archetype, list_url
            )

    # ── /mdeck list ───────────────────────────────────────────────────────────

    @mdeck_group.command(name="list", description="Show all your registered decks for a format.")
    @app_commands.describe(format="The Magic format.")
    @app_commands.autocomplete(format=magic_format_autocomplete)
    async def list_decks(
        self, interaction: discord.Interaction, format: str
    ) -> None:
        async with db_session_manager():
            await self._handle_list(interaction, normalize_format(format))

    # ── /mdeck use ────────────────────────────────────────────────────────────

    @mdeck_group.command(name="use", description="Set a deck as your active deck for a format.")
    @app_commands.describe(
        format="The Magic format.",
        name="Name of the deck to activate.",
    )
    @app_commands.autocomplete(format=magic_format_autocomplete)
    async def use(
        self, interaction: discord.Interaction, format: str, name: str
    ) -> None:
        async with db_session_manager():
            await self._handle_use(interaction, normalize_format(format), name)

    # ── /mdeck delete ─────────────────────────────────────────────────────────

    @mdeck_group.command(name="delete", description="Delete one of your decks.")
    @app_commands.describe(
        format="The Magic format.",
        name="Name of the deck to delete.",
    )
    @app_commands.autocomplete(format=magic_format_autocomplete)
    async def delete(
        self, interaction: discord.Interaction, format: str, name: str
    ) -> None:
        async with db_session_manager():
            await self._handle_delete(interaction, normalize_format(format), name)

    # ── /mdeck set-list ───────────────────────────────────────────────────────

    @mdeck_group.command(name="set-list", description="Update the deck list URL for a deck.")
    @app_commands.describe(
        format="The Magic format.",
        name="Deck name.",
        list_url="New deck list URL.",
    )
    @app_commands.autocomplete(format=magic_format_autocomplete)
    async def set_list(
        self,
        interaction: discord.Interaction,
        format: str,
        name: str,
        list_url: str,
    ) -> None:
        async with db_session_manager():
            await self._handle_set_list(interaction, normalize_format(format), name, list_url)

    # ── /mdeck stats ──────────────────────────────────────────────────────────

    @mdeck_group.command(
        name="stats", description="View win/loss stats for a deck."
    )
    @app_commands.describe(
        format="The Magic format.",
        name="Deck name (leave blank for your active deck).",
    )
    @app_commands.autocomplete(format=magic_format_autocomplete)
    async def stats(
        self,
        interaction: discord.Interaction,
        format: str,
        name: str | None = None,
    ) -> None:
        async with db_session_manager():
            await self._handle_stats(interaction, normalize_format(format), name)

    # ── implementations ───────────────────────────────────────────────────────

    async def _handle_create(
        self,
        interaction: discord.Interaction,
        fmt: str,
        name: str,
        archetype: str | None,
        list_url: str | None,
    ) -> None:
        assert interaction.guild is not None
        from seer.services import WargameArmiesService, WargameConfigService

        if len(name) > 64:
            await interaction.response.send_message(
                "Deck name must be 64 characters or fewer.", ephemeral=True
            )
            return
        if archetype and len(archetype) > 64:
            await interaction.response.send_message(
                "Archetype label must be 64 characters or fewer.", ephemeral=True
            )
            return
        if list_url and not validate_deck_url(list_url):
            valid = ", ".join(f"`{h}`" for h in sorted(VALID_DECK_LIST_HOSTS))
            await interaction.response.send_message(
                f"Deck list URL must be from one of: {valid}.", ephemeral=True
            )
            return

        cfg_svc = WargameConfigService()
        config = await cfg_svc.upsert(interaction.guild.id)
        armies_svc = WargameArmiesService()
        count = await armies_svc.count(interaction.guild.id, interaction.user.id, fmt)
        if count >= config.army_limit:
            await interaction.response.send_message(
                f"You have reached the deck limit of {config.army_limit} for {display_format(fmt)}.",
                ephemeral=True,
            )
            return

        existing = await armies_svc.get_by_name(
            interaction.guild.id, interaction.user.id, fmt, name
        )
        if existing:
            await interaction.response.send_message(
                f'You already have a {display_format(fmt)} deck named "{name}".', ephemeral=True
            )
            return

        await armies_svc.create(
            interaction.guild.id,
            interaction.user.id,
            fmt,
            name,
            faction=archetype,
            list_url=list_url,
            set_as_current=True,
        )
        await interaction.response.send_message(
            f'✅ Deck **{name}** created and set as your active {display_format(fmt)} deck.',
            ephemeral=True,
        )

    async def _handle_list(self, interaction: discord.Interaction, fmt: str) -> None:
        assert interaction.guild is not None
        from seer.services import WargameArmiesService

        armies_svc = WargameArmiesService()
        decks = await armies_svc.list_all(interaction.guild.id, interaction.user.id, fmt)
        if not decks:
            await interaction.response.send_message(
                f"You have no registered {display_format(fmt)} decks. "
                "Use `/mdeck create` to add one.",
                ephemeral=True,
            )
            return

        profile = await armies_svc.get_profile(interaction.guild.id, interaction.user.id, fmt)
        current_id = profile.current_army_id

        lines = []
        for deck in decks:
            marker = "▶ " if deck.id == current_id else "  "
            label = deck.name
            if deck.faction:
                label += f" ({deck.faction})"
            lines.append(
                f"{marker}[{label}]({deck.list_url})" if deck.list_url else f"{marker}{label}"
            )

        embed = discord.Embed(
            title=f"Your {display_format(fmt)} Decks",
            description="\n".join(lines),
            color=discord.Color.blue(),
        )
        embed.set_footer(text="▶ = currently active deck")
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _handle_use(
        self, interaction: discord.Interaction, fmt: str, name: str
    ) -> None:
        assert interaction.guild is not None
        from seer.services import WargameArmiesService

        armies_svc = WargameArmiesService()
        deck = await armies_svc.get_by_name(interaction.guild.id, interaction.user.id, fmt, name)
        if deck is None:
            await interaction.response.send_message(
                f'You have no {display_format(fmt)} deck named "{name}".', ephemeral=True
            )
            return
        await armies_svc.set_current(interaction.guild.id, interaction.user.id, fmt, deck)
        await interaction.response.send_message(
            f'✅ **{name}** is now your active {display_format(fmt)} deck.', ephemeral=True
        )

    async def _handle_delete(
        self, interaction: discord.Interaction, fmt: str, name: str
    ) -> None:
        assert interaction.guild is not None
        from seer.services import WargameArmiesService

        armies_svc = WargameArmiesService()
        deck = await armies_svc.get_by_name(interaction.guild.id, interaction.user.id, fmt, name)
        if deck is None:
            await interaction.response.send_message(
                f'You have no {display_format(fmt)} deck named "{name}".', ephemeral=True
            )
            return
        await armies_svc.delete(interaction.guild.id, interaction.user.id, deck)
        await interaction.response.send_message(
            f'🗑️ Deck **{name}** has been deleted.', ephemeral=True
        )

    async def _handle_set_list(
        self,
        interaction: discord.Interaction,
        fmt: str,
        name: str,
        list_url: str,
    ) -> None:
        assert interaction.guild is not None
        from seer.services import WargameArmiesService

        if not validate_deck_url(list_url):
            valid = ", ".join(f"`{h}`" for h in sorted(VALID_DECK_LIST_HOSTS))
            await interaction.response.send_message(
                f"Deck list URL must be from one of: {valid}.", ephemeral=True
            )
            return

        armies_svc = WargameArmiesService()
        deck = await armies_svc.get_by_name(interaction.guild.id, interaction.user.id, fmt, name)
        if deck is None:
            await interaction.response.send_message(
                f'You have no {display_format(fmt)} deck named "{name}".', ephemeral=True
            )
            return
        await armies_svc.set_list_url(deck, list_url)
        await interaction.response.send_message(
            f'✅ Deck list updated for **{name}**.', ephemeral=True
        )

    async def _handle_stats(
        self, interaction: discord.Interaction, fmt: str, name: str | None
    ) -> None:
        assert interaction.guild is not None
        from seer.services import WargameArmiesService, WargameSeasonsService

        armies_svc = WargameArmiesService()
        if name is None:
            profile = await armies_svc.get_profile(interaction.guild.id, interaction.user.id, fmt)
            if not profile.current_army_id:
                await interaction.response.send_message(
                    f"You have no active {display_format(fmt)} deck. Use `/mdeck use` to select one.",
                    ephemeral=True,
                )
                return
            deck = await armies_svc.get_by_id(profile.current_army_id)
        else:
            deck = await armies_svc.get_by_name(
                interaction.guild.id, interaction.user.id, fmt, name
            )

        if deck is None:
            await interaction.response.send_message(
                f'No {display_format(fmt)} deck named "{name}" found.' if name else "Deck not found.",
                ephemeral=True,
            )
            return

        all_stats = await armies_svc.get_army_stats(
            interaction.guild.id, interaction.user.id, deck.id
        )
        label = deck.name
        if deck.faction:
            label += f" ({deck.faction})"
        display_label = f"[{label}]({deck.list_url})" if deck.list_url else label

        embed = discord.Embed(
            title=f"🃏 Deck Stats — {deck.name}",
            description=f"Overall statistics for {display_label}.",
            color=discord.Color.blue(),
        )
        if deck.list_url:
            embed.url = deck.list_url
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

        seasons_svc = WargameSeasonsService()
        active = await seasons_svc.get_active(interaction.guild.id, fmt)
        if active:
            from seer.services import WargameMatchesService
            matches_svc = WargameMatchesService()
            s_matches = await matches_svc.get_for_user(
                interaction.guild.id, interaction.user.id,
                season_id=active.id, army_id=deck.id,
            )
            sw = sum(1 for m in s_matches if m.winner_xid == interaction.user.id)
            sd = sum(1 for m in s_matches if m.winner_xid is None)
            sl = len(s_matches) - sw - sd
            sr = round(sw / len(s_matches) * 100) if s_matches else 0
            embed.add_field(
                name=f"This Season ({active.name})",
                value=f"{len(s_matches)} games · {sw}W {sd}D {sl}L · {sr}% win rate",
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: Seer) -> None:  # pragma: no cover
    await bot.add_cog(MDeckCog(bot), guild=settings.GUILD_OBJECT)
