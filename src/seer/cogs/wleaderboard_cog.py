from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from seer.database import db_session_manager
from seer.settings import settings
from seer.utils import for_all_callbacks, is_guild

from ._wargame_helpers import display_game, game_system_autocomplete

if TYPE_CHECKING:
    from seer import Seer

logger = logging.getLogger(__name__)


@for_all_callbacks(app_commands.check(is_guild))
class WLeaderboardCog(commands.Cog):
    def __init__(self, bot: Seer) -> None:
        self.bot = bot

    @app_commands.command(
        name="wleaderboard",
        description="Display the wargame season leaderboard.",
    )
    @app_commands.describe(
        game_system="The game system.",
        season="Season name (leave blank for current season).",
    )
    @app_commands.autocomplete(game_system=game_system_autocomplete)
    async def wleaderboard(
        self,
        interaction: discord.Interaction,
        game_system: str,
        season: str | None = None,
    ) -> None:
        async with db_session_manager():
            await self._handle_leaderboard(interaction, game_system, season)

    async def _handle_leaderboard(
        self,
        interaction: discord.Interaction,
        game_system: str,
        season_name: str | None,
    ) -> None:
        assert interaction.guild is not None
        from seer.services import (
            WargameConfigService,
            WargameMatchesService,
            WargameSeasonsService,
        )

        game_label = display_game(game_system)
        seasons_svc = WargameSeasonsService()

        if season_name is None:
            season = await seasons_svc.get_active(interaction.guild.id, game_system)
            if season is None:
                await interaction.response.send_message(
                    f"There is no active {game_label} season.", ephemeral=True
                )
                return
        else:
            season = await seasons_svc.get_by_name(
                interaction.guild.id, game_system, season_name
            )
            if season is None:
                await interaction.response.send_message(
                    f'No {game_label} season named "{season_name}" found.', ephemeral=True
                )
                return

        cfg_svc = WargameConfigService()
        config = await cfg_svc.upsert(interaction.guild.id)

        matches_svc = WargameMatchesService()
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
            title=f"{game_label} Leaderboard — {season.name}",
            color=discord.Color.purple(),
        )

        if not eligible:
            embed.description = (
                f"Not enough data yet — players need at least **{config.minimum_games}** "
                f"confirmed game{'s' if config.minimum_games != 1 else ''} to appear."
            )
        else:
            embed.description = "Current standings for the season."
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


async def setup(bot: Seer) -> None:  # pragma: no cover
    await bot.add_cog(WLeaderboardCog(bot), guild=settings.GUILD_OBJECT)
