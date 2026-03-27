from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from seer.database import db_session_manager
from seer.settings import settings
from seer.utils import for_all_callbacks, is_guild

if TYPE_CHECKING:
    from seer import Seer

logger = logging.getLogger(__name__)


@for_all_callbacks(app_commands.check(is_guild))
class SeasonCog(commands.Cog):
    def __init__(self, bot: Seer) -> None:
        self.bot = bot

    season_group = app_commands.Group(name="season", description="Manage Magic: The Gathering Commander (EDH) seasons.")

    # ── /season info ──────────────────────────────────────────────────────────

    @season_group.command(name="info", description="View info about a season.")
    @app_commands.describe(name="Season name (leave blank for current season).")
    async def info(self, interaction: discord.Interaction, name: str | None = None) -> None:
        async with db_session_manager():
            await self._handle_info(interaction, name)

    # ── /season start ─────────────────────────────────────────────────────────

    @season_group.command(name="start", description="Start a new season.")
    @app_commands.describe(name="Name for the new season.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def start(self, interaction: discord.Interaction, name: str) -> None:
        async with db_session_manager():
            await self._handle_start(interaction, name)

    # ── /season end ───────────────────────────────────────────────────────────

    @season_group.command(name="end", description="End the current season.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def end(self, interaction: discord.Interaction) -> None:
        async with db_session_manager():
            await self._handle_end(interaction)

    # ── implementations ───────────────────────────────────────────────────────

    async def _handle_info(
        self, interaction: discord.Interaction, name: str | None
    ) -> None:
        assert interaction.guild is not None
        from seer.services import LeagueSeasonsService

        seasons_svc = LeagueSeasonsService()
        if name is None:
            season = await seasons_svc.get_active(interaction.guild.id)
            if season is None:
                await interaction.response.send_message(
                    "There is no active season.", ephemeral=True
                )
                return
        else:
            season = await seasons_svc.get_by_name(interaction.guild.id, name)
            if season is None:
                await interaction.response.send_message(
                    f'No season named "{name}" found.', ephemeral=True
                )
                return

        match_count = await seasons_svc.count_matches(season.id)

        start_ts = int(season.start_date.timestamp())
        end_ts = int(season.end_date.timestamp()) if season.end_date else None

        embed = discord.Embed(
            title=f"Season — {season.name}",
            description=(
                "This is the **current active season**."
                if season.end_date is None
                else "This season has ended."
            ),
            color=discord.Color.green() if season.end_date is None else discord.Color.greyple(),
        )
        embed.add_field(name="Started", value=f"<t:{start_ts}:F>")
        embed.add_field(
            name="Ended",
            value=f"<t:{end_ts}:F>" if end_ts else "Still in progress",
        )
        embed.add_field(
            name="Confirmed Matches",
            value=f"{match_count} game{'s' if match_count != 1 else ''}",
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _handle_start(self, interaction: discord.Interaction, name: str) -> None:
        assert interaction.guild is not None
        from seer.services import LeagueSeasonsService

        seasons_svc = LeagueSeasonsService()

        # Check if there's already an active season
        active = await seasons_svc.get_active(interaction.guild.id)
        if active is not None:
            await interaction.response.send_message(
                f'There is already an active season: **{active.name}**. End it first with `/season end`.',
                ephemeral=True,
            )
            return

        # Check for name collision
        existing = await seasons_svc.get_by_name(interaction.guild.id, name)
        if existing is not None:
            await interaction.response.send_message(
                f'A season named "{name}" already exists.', ephemeral=True
            )
            return

        season = await seasons_svc.create(interaction.guild.id, name)
        start_ts = int(season.start_date.timestamp())
        await interaction.response.send_message(
            f'✅ Season **{name}** has started! (<t:{start_ts}:F>)', ephemeral=False
        )

    async def _handle_end(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None
        from seer.services import LeagueSeasonsService

        seasons_svc = LeagueSeasonsService()
        ended = await seasons_svc.end_active(interaction.guild.id)
        if ended is None:
            await interaction.response.send_message(
                "There is no active season to end.", ephemeral=True
            )
            return

        await interaction.response.send_message(
            f'✅ Season **{ended.name}** has ended. Use `/leaderboard` to see final standings.',
            ephemeral=False,
        )


async def setup(bot: Seer) -> None:  # pragma: no cover
    await bot.add_cog(SeasonCog(bot), guild=settings.GUILD_OBJECT)
