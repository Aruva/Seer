from __future__ import annotations

import logging

import discord
from ddtrace.trace import tracer
from discord import Color, Embed, app_commands
from discord.ext import commands

from seer import Seer, __version__
from seer.metrics import add_span_context
from seer.operations import safe_send_channel
from seer.settings import settings
from seer.utils import for_all_callbacks, is_guild

logger = logging.getLogger(__name__)

ISSUES = "https://github.com/Southsidestudio/Seer/issues"
PATREON = "https://southsidestudioandhobbies.com"
BOT_NAME = "SouthSeer"
BOT_TAGLINE = "Your league tracker for MTG and tabletop wargames — brought to you by Southside Studio and Hobbies."


@for_all_callbacks(app_commands.check(is_guild))
class AboutCog(commands.Cog):
    def __init__(self, bot: Seer) -> None:
        self.bot = bot

    @app_commands.command(name="about", description="Get information about SouthSeer.")
    @tracer.wrap(name="interaction", resource="about")
    async def about(self, interaction: discord.Interaction) -> None:
        add_span_context(interaction)
        embed = Embed(title=BOT_NAME)
        embed.set_thumbnail(url=settings.thumb(interaction.guild_id))
        version = f"v{__version__}"
        embed.add_field(name="Version", value=version)
        embed.add_field(name="Home", value="[Southside Studio and Hobbies](https://southsidestudioandhobbies.com)")
        embed.description = (
            f"_{BOT_TAGLINE}_\n"
            "\n"
            f"[🔗 Add SouthSeer to your Discord!]({settings.BOT_INVITE_LINK})\n"
            "\n"
            "SouthSeer tracks EDH league matches, wargame results, seasons, "
            "leaderboards, and deck/army rosters — all in one place.\n"
            "\n"
            f"Found a bug? Please [report it here]({ISSUES})."
        )
        embed.color = Color(settings.INFO_EMBED_COLOR)
        await safe_send_channel(interaction, embed=embed)


async def setup(bot: Seer) -> None:  # pragma: no cover
    await bot.add_cog(AboutCog(bot), guild=settings.GUILD_OBJECT)
