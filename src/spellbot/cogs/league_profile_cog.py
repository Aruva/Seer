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
class LeagueProfileCog(commands.Cog):
    def __init__(self, bot: SpellBot) -> None:
        self.bot = bot

    @app_commands.command(
        name="profile",
        description="View your Magic: The Gathering Commander (EDH) profile and match statistics.",
    )
    async def profile(self, interaction: discord.Interaction) -> None:
        async with db_session_manager():
            await self._handle_profile(interaction)

    async def _handle_profile(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None
        from spellbot.services import (
            LeagueConfigService,
            LeagueDecksService,
            LeagueMatchesService,
            LeagueSeasonsService,
        )
        from spellbot.services.league_elo import LeagueEloService

        decks_svc = LeagueDecksService()
        profile = await decks_svc.get_profile(interaction.guild.id, interaction.user.id)

        embed = discord.Embed(
            title="League Profile",
            description=f"Statistics for <@{interaction.user.id}>",
            color=discord.Color.blue(),
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        # ELO rating — shown prominently at the top
        elo_svc = LeagueEloService()
        elo, games_played = await elo_svc.get_for_user(interaction.guild.id, interaction.user.id)
        if games_played == 0:
            elo_display = f"**{elo}** *(unranked — play your first match!)*"
        else:
            # Rough tier labels for flavour
            if elo >= 1800:
                tier = "⚡ Champion"
            elif elo >= 1600:
                tier = "🔥 Expert"
            elif elo >= 1400:
                tier = "⚔️ Veteran"
            elif elo >= 1200:
                tier = "🌱 Developing"
            else:
                tier = "🆕 Newcomer"
            elo_display = f"**{elo}** — {tier} ({games_played} games)"
        embed.add_field(name="ELO Rating", value=elo_display, inline=False)

        # Current deck
        if profile.current_deck_id:
            deck = await decks_svc.get_by_id(profile.current_deck_id)
            if deck:
                deck_text = f"[{deck.name}]({deck.deck_list})" if deck.deck_list else deck.name
            else:
                deck_text = "Not set"
        else:
            deck_text = "Not set — use `/deck use` to select one"
        embed.add_field(name="Active Deck", value=deck_text, inline=False)

        # All-time stats (confirmed matches)
        matches_svc = LeagueMatchesService()
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
        seasons_svc = LeagueSeasonsService()
        active = await seasons_svc.get_active(interaction.guild.id)
        if active:
            s_matches = await matches_svc.get_for_user(
                interaction.guild.id, interaction.user.id, season_id=active.id
            )
            sw = sum(1 for m in s_matches if m.winner_xid == interaction.user.id)
            sd = sum(1 for m in s_matches if m.winner_xid is None)
            sl = len(s_matches) - sw - sd
            sr = round(sw / len(s_matches) * 100) if s_matches else 0

            cfg_svc = LeagueConfigService()
            config = await cfg_svc.upsert(interaction.guild.id)
            points = sw * config.points_gained + sd * config.points_per_draw - sl * config.points_lost
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
    await bot.add_cog(LeagueProfileCog(bot), guild=settings.GUILD_OBJECT)
