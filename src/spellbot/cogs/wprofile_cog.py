from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from spellbot.database import db_session_manager
from spellbot.settings import settings
from spellbot.utils import for_all_callbacks, is_guild

from ._wargame_helpers import display_game, game_system_autocomplete

if TYPE_CHECKING:
    from spellbot import SpellBot

logger = logging.getLogger(__name__)


@for_all_callbacks(app_commands.check(is_guild))
class WProfileCog(commands.Cog):
    def __init__(self, bot: SpellBot) -> None:
        self.bot = bot

    @app_commands.command(
        name="wprofile",
        description="View your wargame profile and match statistics.",
    )
    @app_commands.describe(game_system="The game system to show stats for.")
    @app_commands.autocomplete(game_system=game_system_autocomplete)
    async def wprofile(
        self,
        interaction: discord.Interaction,
        game_system: str,
    ) -> None:
        async with db_session_manager():
            await self._handle_profile(interaction, game_system)

    async def _handle_profile(
        self,
        interaction: discord.Interaction,
        game_system: str,
    ) -> None:
        assert interaction.guild is not None
        from spellbot.services import (
            WargameArmiesService,
            WargameConfigService,
            WargameEloService,
            WargameMatchesService,
            WargameSeasonsService,
        )

        game_label = display_game(game_system)

        armies_svc = WargameArmiesService()
        profile = await armies_svc.get_profile(
            interaction.guild.id, interaction.user.id, game_system
        )

        elo_svc = WargameEloService()
        elo_row = await elo_svc.get_for_user(
            interaction.guild.id, interaction.user.id, game_system
        )

        embed = discord.Embed(
            title=f"{game_label} Profile",
            description=f"Statistics for <@{interaction.user.id}>",
            color=discord.Color.blue(),
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        # ELO rating (shown at the top)
        elo_val = elo_row.elo
        g = elo_row.games_played
        if g == 0:
            elo_display = f"**{elo_val}** *(unrated — play your first confirmed match!)*"
        else:
            if elo_val >= 1700:
                tier = "Champion"
            elif elo_val >= 1600:
                tier = "Expert"
            elif elo_val >= 1500:
                tier = "Veteran"
            elif g < 30:
                tier = "Newcomer"
            else:
                tier = "Developing"
            elo_display = f"**{elo_val}** — {tier} *({g} games)*"
        embed.add_field(name="🎯 ELO Rating", value=elo_display, inline=False)

        # Current army
        if profile.current_army_id:
            army = await armies_svc.get_by_id(profile.current_army_id)
            if army:
                label = army.name
                if army.faction:
                    label += f" ({army.faction})"
                army_text = f"[{label}]({army.list_url})" if army.list_url else label
            else:
                army_text = "Not set"
        else:
            army_text = "Not set — use `/army use` to select one"
        embed.add_field(name="Active Army", value=army_text, inline=False)

        # All-time stats (confirmed matches)
        matches_svc = WargameMatchesService()
        all_matches = await matches_svc.get_for_user(interaction.guild.id, interaction.user.id)
        total = len(all_matches)
        wins = sum(1 for m in all_matches if m.winner_xid == interaction.user.id)
        draws = sum(1 for m in all_matches if m.winner_xid is None)
        losses = total - wins - draws
        win_rate = round(wins / total * 100) if total else 0

        embed.add_field(name="Total Matches", value=str(total))
        embed.add_field(name="Wins", value=str(wins))
        embed.add_field(name="Draws", value=str(draws))
        embed.add_field(name="Losses", value=str(losses))
        embed.add_field(name="Win Rate", value=f"{win_rate}%")

        # Current season breakdown
        seasons_svc = WargameSeasonsService()
        active = await seasons_svc.get_active(interaction.guild.id, game_system)
        if active:
            s_matches = await matches_svc.get_for_user(
                interaction.guild.id, interaction.user.id, season_id=active.id
            )
            sw = sum(1 for m in s_matches if m.winner_xid == interaction.user.id)
            sd = sum(1 for m in s_matches if m.winner_xid is None)
            sl = len(s_matches) - sw - sd
            sr = round(sw / len(s_matches) * 100) if s_matches else 0

            cfg_svc = WargameConfigService()
            config = await cfg_svc.upsert(interaction.guild.id)
            points = (
                sw * config.points_gained
                + sd * config.points_per_draw
                - sl * config.points_lost
            )
            display_points = config.base_points + points

            embed.add_field(
                name=f"Season: {active.name}",
                value=(
                    f"{len(s_matches)} games · {sw}W {sd}D {sl}L · {sr}% win rate\n"
                    f"**{display_points} points**"
                ),
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: SpellBot) -> None:  # pragma: no cover
    await bot.add_cog(WProfileCog(bot), guild=settings.GUILD_OBJECT)
