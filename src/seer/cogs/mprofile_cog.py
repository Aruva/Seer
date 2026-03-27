from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from seer.database import db_session_manager
from seer.settings import settings
from seer.utils import for_all_callbacks, is_guild

from ._magic_helpers import display_format, magic_format_autocomplete, normalize_format

if TYPE_CHECKING:
    from seer import Seer

logger = logging.getLogger(__name__)


@for_all_callbacks(app_commands.check(is_guild))
class MProfileCog(commands.Cog):
    def __init__(self, bot: Seer) -> None:
        self.bot = bot

    @app_commands.command(
        name="mprofile",
        description="View your Magic: The Gathering league profile and match statistics.",
    )
    @app_commands.describe(format="The Magic format to show stats for.")
    @app_commands.autocomplete(format=magic_format_autocomplete)
    async def mprofile(
        self,
        interaction: discord.Interaction,
        format: str,
    ) -> None:
        async with db_session_manager():
            await self._handle_profile(interaction, normalize_format(format))

    async def _handle_profile(self, interaction: discord.Interaction, fmt: str) -> None:
        assert interaction.guild is not None
        from seer.services import (
            WargameArmiesService,
            WargameConfigService,
            WargameEloService,
            WargameMatchesService,
            WargameSeasonsService,
        )

        fmt_label = display_format(fmt)

        elo_svc = WargameEloService()
        elo_row = await elo_svc.get_for_user(interaction.guild.id, interaction.user.id, fmt)

        embed = discord.Embed(
            title=f"🃏 {fmt_label} Profile",
            description=f"Statistics for <@{interaction.user.id}>",
            color=discord.Color.blue(),
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        # ELO rating
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

        # Active deck
        armies_svc = WargameArmiesService()
        profile = await armies_svc.get_profile(interaction.guild.id, interaction.user.id, fmt)
        if profile.current_army_id:
            deck = await armies_svc.get_by_id(profile.current_army_id)
            if deck:
                label = deck.name
                if deck.faction:
                    label += f" ({deck.faction})"
                deck_text = f"[{label}]({deck.list_url})" if deck.list_url else label
            else:
                deck_text = "Not set"
        else:
            deck_text = "Not set — use `/mdeck use` to select one"
        embed.add_field(name="Active Deck", value=deck_text, inline=False)

        # All-time stats
        matches_svc = WargameMatchesService()
        all_matches = await matches_svc.get_for_user(interaction.guild.id, interaction.user.id)
        # Filter to this format via season game_system
        from seer.database import DatabaseSession
        from seer.models import WargameSeason
        fmt_season_ids = {
            s.id for s in
            DatabaseSession.query(WargameSeason)
            .filter(WargameSeason.guild_xid == interaction.guild.id, WargameSeason.game_system == fmt)
            .all()
        }
        fmt_matches = [m for m in all_matches if m.season_id in fmt_season_ids]
        total = len(fmt_matches)
        wins = sum(1 for m in fmt_matches if m.winner_xid == interaction.user.id)
        draws = sum(1 for m in fmt_matches if m.winner_xid is None)
        losses = total - wins - draws
        win_rate = round(wins / total * 100) if total else 0

        embed.add_field(name="Total Matches", value=str(total))
        embed.add_field(name="Wins", value=str(wins))
        embed.add_field(name="Draws", value=str(draws))
        embed.add_field(name="Losses", value=str(losses))
        embed.add_field(name="Win Rate", value=f"{win_rate}%")

        # Current season
        seasons_svc = WargameSeasonsService()
        active = await seasons_svc.get_active(interaction.guild.id, fmt)
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
            pts = sw * config.points_gained + sd * config.points_per_draw - sl * config.points_lost
            display_pts = config.base_points + pts

            embed.add_field(
                name=f"Season: {active.name}",
                value=(
                    f"{len(s_matches)} games · {sw}W {sd}D {sl}L · {sr}% win rate\n"
                    f"**{display_pts} points**"
                ),
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: Seer) -> None:  # pragma: no cover
    await bot.add_cog(MProfileCog(bot), guild=settings.GUILD_OBJECT)
