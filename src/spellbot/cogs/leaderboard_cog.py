from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from spellbot.database import db_session_manager
from spellbot.settings import settings
from spellbot.utils import for_all_callbacks, is_guild

if TYPE_CHECKING:
    from spellbot import SpellBot

logger = logging.getLogger(__name__)


@for_all_callbacks(app_commands.check(is_guild))
class LeaderboardCog(commands.Cog):
    def __init__(self, bot: SpellBot) -> None:
        self.bot = bot

    @app_commands.command(
        name="leaderboard",
        description="Display the Magic: The Gathering Commander (EDH) season leaderboard.",
    )
    @app_commands.describe(season="Season name (leave blank for current season).")
    async def leaderboard(
        self, interaction: discord.Interaction, season: str | None = None
    ) -> None:
        async with db_session_manager():
            await self._handle_leaderboard(interaction, season)

    async def _handle_leaderboard(
        self, interaction: discord.Interaction, season_name: str | None
    ) -> None:
        assert interaction.guild is not None
        from spellbot.services import (
            LeagueConfigService,
            LeagueMatchesService,
            LeagueSeasonsService,
        )

        seasons_svc = LeagueSeasonsService()
        if season_name is None:
            season = await seasons_svc.get_active(interaction.guild.id)
            if season is None:
                await interaction.response.send_message(
                    "There is no active season.", ephemeral=True
                )
                return
        else:
            season = await seasons_svc.get_by_name(interaction.guild.id, season_name)
            if season is None:
                await interaction.response.send_message(
                    f'No season named "{season_name}" found.', ephemeral=True
                )
                return

        cfg_svc = LeagueConfigService()
        config = await cfg_svc.upsert(interaction.guild.id)

        matches_svc = LeagueMatchesService()
        standings = await matches_svc.get_leaderboard(interaction.guild.id, season.id)

        # Apply points formula and filter by minimum games
        for s in standings:
            s["points"] = (
                s["wins"] * config.points_gained
                + s["draws"] * config.points_per_draw
                - s["losses"] * config.points_lost
            )
            s["display_points"] = config.base_points + s["points"]

        eligible = [s for s in standings if s["matches"] >= config.minimum_games]
        eligible.sort(
            key=lambda s: (
                -s["display_points"],
                -(s["wins"] / s["matches"]) if s["matches"] else 0,
            )
        )

        embed = discord.Embed(
            title=f"Leaderboard — {season.name}",
            color=discord.Color.purple(),
        )

        if not eligible:
            embed.description = (
                f"Not enough data yet — players need at least **{config.minimum_games}** "
                f"confirmed game{'s' if config.minimum_games != 1 else ''} to appear."
            )
        else:
            embed.description = "Current standings for the season."
            # Build three inline columns
            player_lines = []
            games_lines = []
            points_lines = []

            for i, s in enumerate(eligible[:25], start=1):
                win_rate = round(s["wins"] / s["matches"] * 100) if s["matches"] else 0
                player_lines.append(f"{i}. <@{s['user_xid']}>")
                games_lines.append(
                    f"{s['matches']} game{'s' if s['matches'] != 1 else ''} ({win_rate}% wr)"
                )
                points_lines.append(str(s["display_points"]))

            embed.add_field(name="Player", value="\n".join(player_lines), inline=True)
            embed.add_field(name="Games", value="\n".join(games_lines), inline=True)
            embed.add_field(name="Points", value="\n".join(points_lines), inline=True)

        await interaction.response.send_message(embed=embed)


async def setup(bot: SpellBot) -> None:  # pragma: no cover
    await bot.add_cog(LeaderboardCog(bot), guild=settings.GUILD_OBJECT)
