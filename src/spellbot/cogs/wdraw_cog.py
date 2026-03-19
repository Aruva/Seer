from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from spellbot.database import db_session_manager
from spellbot.settings import settings
from spellbot.utils import for_all_callbacks, is_guild

from ._wargame_helpers import game_system_autocomplete, log_wargame_match

if TYPE_CHECKING:
    from spellbot import SpellBot

logger = logging.getLogger(__name__)


@for_all_callbacks(app_commands.check(is_guild))
class WDrawCog(commands.Cog):
    def __init__(self, bot: SpellBot) -> None:
        self.bot = bot

    @app_commands.command(
        name="wdraw",
        description="Log a wargame match draw against an opponent.",
    )
    @app_commands.describe(
        game_system="The game system played.",
        opponent="Your opponent in the match.",
    )
    @app_commands.autocomplete(game_system=game_system_autocomplete)
    async def wdraw(
        self,
        interaction: discord.Interaction,
        game_system: str,
        opponent: discord.Member,
    ) -> None:
        async with db_session_manager():
            await log_wargame_match(
                self.bot,
                interaction,
                game_system=game_system,
                opponent=opponent,
                is_win=False,
            )


async def setup(bot: SpellBot) -> None:  # pragma: no cover
    await bot.add_cog(WDrawCog(bot), guild=settings.GUILD_OBJECT)
