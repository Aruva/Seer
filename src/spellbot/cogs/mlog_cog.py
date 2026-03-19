from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from spellbot.database import db_session_manager
from spellbot.settings import settings
from spellbot.utils import for_all_callbacks, is_guild

from ._magic_helpers import log_magic_match, magic_format_autocomplete

if TYPE_CHECKING:
    from spellbot import SpellBot

logger = logging.getLogger(__name__)


@for_all_callbacks(app_commands.check(is_guild))
class MLogCog(commands.Cog):
    def __init__(self, bot: SpellBot) -> None:
        self.bot = bot

    @app_commands.command(
        name="mlog",
        description="Log a Magic: The Gathering 1v1 match win.",
    )
    @app_commands.describe(
        format="The Magic format played (Standard, Modern, Pioneer, etc.).",
        opponent="Your opponent in the match.",
    )
    @app_commands.autocomplete(format=magic_format_autocomplete)
    async def mlog(
        self,
        interaction: discord.Interaction,
        format: str,
        opponent: discord.Member,
    ) -> None:
        async with db_session_manager():
            await log_magic_match(self.bot, interaction, format, opponent, is_win=True)


async def setup(bot: SpellBot) -> None:  # pragma: no cover
    await bot.add_cog(MLogCog(bot), guild=settings.GUILD_OBJECT)
