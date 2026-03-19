from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from spellbot.database import db_session_manager
from spellbot.settings import settings
from spellbot.utils import for_all_callbacks, is_guild

from ._magic_helpers import display_format, magic_format_autocomplete, normalize_format

if TYPE_CHECKING:
    from spellbot import SpellBot

logger = logging.getLogger(__name__)


@for_all_callbacks(app_commands.check(is_guild))
class MSeasonCog(commands.Cog):
    def __init__(self, bot: SpellBot) -> None:
        self.bot = bot

    mseason_group = app_commands.Group(
        name="mseason",
        description="Manage Magic: The Gathering league seasons.",
    )

    @mseason_group.command(name="info", description="View info about a Magic season.")
    @app_commands.describe(
        format="The Magic format.",
        name="Season name (leave blank for current season).",
    )
    @app_commands.autocomplete(format=magic_format_autocomplete)
    async def info(
        self, interaction: discord.Interaction, format: str, name: str | None = None
    ) -> None:
        async with db_session_manager():
            await self._handle_info(interaction, normalize_format(format), name)

    @mseason_group.command(name="start", description="Start a new Magic season.")
    @app_commands.describe(
        format="The Magic format.",
        name="Name for the new season.",
    )
    @app_commands.autocomplete(format=magic_format_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def start(
        self, interaction: discord.Interaction, format: str, name: str
    ) -> None:
        async with db_session_manager():
            await self._handle_start(interaction, normalize_format(format), name)

    @mseason_group.command(name="end", description="End the current Magic season.")
    @app_commands.describe(format="The Magic format.")
    @app_commands.autocomplete(format=magic_format_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def end(self, interaction: discord.Interaction, format: str) -> None:
        async with db_session_manager():
            await self._handle_end(interaction, normalize_format(format))

    # ── implementations ───────────────────────────────────────────────────────

    async def _handle_info(
        self, interaction: discord.Interaction, fmt: str, name: str | None
    ) -> None:
        assert interaction.guild is not None
        from spellbot.services import WargameMatchesService, WargameSeasonsService

        fmt_label = display_format(fmt)
        seasons_svc = WargameSeasonsService()

        if name is None:
            season = await seasons_svc.get_active(interaction.guild.id, fmt)
            if season is None:
                await interaction.response.send_message(
                    f"There is no active {fmt_label} season.", ephemeral=True
                )
                return
        else:
            season = await seasons_svc.get_by_name(interaction.guild.id, fmt, name)
            if season is None:
                await interaction.response.send_message(
                    f'No {fmt_label} season named "{name}" found.', ephemeral=True
                )
                return

        matches_svc = WargameMatchesService()
        standings = await matches_svc.get_leaderboard(interaction.guild.id, season.id)
        total_matches = sum(s["matches"] for s in standings) // 2

        status = "✅ Active" if season.end_date is None else f"📅 Ended {season.end_date.date()}"
        embed = discord.Embed(
            title=f"🃏 {fmt_label} Season — {season.name}",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Players", value=str(len(standings)), inline=True)
        embed.add_field(name="Matches Played", value=str(total_matches), inline=True)
        embed.add_field(
            name="Started",
            value=season.created_at.strftime("%Y-%m-%d") if hasattr(season, "created_at") else "—",
            inline=True,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _handle_start(
        self, interaction: discord.Interaction, fmt: str, name: str
    ) -> None:
        assert interaction.guild is not None
        from spellbot.services import WargameSeasonsService

        fmt_label = display_format(fmt)
        seasons_svc = WargameSeasonsService()
        existing = await seasons_svc.get_active(interaction.guild.id, fmt)
        if existing:
            await interaction.response.send_message(
                f'A {fmt_label} season is already active: **{existing.name}**. '
                "End it first with `/mseason end`.",
                ephemeral=True,
            )
            return
        await seasons_svc.create(interaction.guild.id, fmt, name)
        await interaction.response.send_message(
            f"✅ {fmt_label} season **{name}** has started!", ephemeral=False
        )

    async def _handle_end(self, interaction: discord.Interaction, fmt: str) -> None:
        assert interaction.guild is not None
        from spellbot.services import WargameSeasonsService

        fmt_label = display_format(fmt)
        seasons_svc = WargameSeasonsService()
        ended = await seasons_svc.end_active(interaction.guild.id, fmt)
        if ended is None:
            await interaction.response.send_message(
                f"There is no active {fmt_label} season to end.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            f"📅 {fmt_label} season **{ended.name}** has ended. Final standings are locked.",
            ephemeral=False,
        )


async def setup(bot: SpellBot) -> None:  # pragma: no cover
    await bot.add_cog(MSeasonCog(bot), guild=settings.GUILD_OBJECT)
