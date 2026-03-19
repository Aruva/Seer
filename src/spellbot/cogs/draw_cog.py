from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from spellbot.database import db_session_manager
from spellbot.settings import settings
from spellbot.utils import for_all_callbacks, is_guild

from ._league_helpers import log_match

if TYPE_CHECKING:
    from spellbot import SpellBot

logger = logging.getLogger(__name__)


@for_all_callbacks(app_commands.check(is_guild))
class DrawCog(commands.Cog):
    def __init__(self, bot: SpellBot) -> None:
        self.bot = bot

    @app_commands.command(
        name="draw",
        description="Log a Magic: The Gathering Commander (EDH) 4-player draw.",
    )
    @app_commands.describe(
        player1="Second player in the match.",
        player2="Third player in the match.",
        player3="Fourth player in the match.",
        my_seat=(
            "The seat number (1–4) you occupied. "
            "List opponents in the remaining seat order for accurate ELO correction."
        ),
    )
    async def draw(
        self,
        interaction: discord.Interaction,
        player1: discord.Member,
        player2: discord.Member,
        player3: discord.Member,
        my_seat: app_commands.Range[int, 1, 4] | None = None,
    ) -> None:
        async with db_session_manager():
            await log_match(
                self.bot,
                interaction,
                player_xids=[
                    interaction.user.id,
                    player1.id,
                    player2.id,
                    player3.id,
                ],
                is_win=False,
                my_seat=my_seat,
            )


async def setup(bot: SpellBot) -> None:  # pragma: no cover
    await bot.add_cog(DrawCog(bot), guild=settings.GUILD_OBJECT)
