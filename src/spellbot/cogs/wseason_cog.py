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
class WSeasonCog(commands.Cog):
    def __init__(self, bot: SpellBot) -> None:
        self.bot = bot

    wseason_group = app_commands.Group(
        name="wseason",
        description="Manage wargame seasons.",
    )

    # ── /wseason info ─────────────────────────────────────────────────────────

    @wseason_group.command(name="info", description="View info about a wargame season.")
    @app_commands.describe(
        game_system="The game system.",
        name="Season name (leave blank for current season).",
    )
    @app_commands.autocomplete(game_system=game_system_autocomplete)
    async def info(
        self,
        interaction: discord.Interaction,
        game_system: str,
        name: str | None = None,
    ) -> None:
        async with db_session_manager():
            await self._handle_info(interaction, game_system, name)

    # ── /wseason start ────────────────────────────────────────────────────────

    @wseason_group.command(name="start", description="Start a new wargame season.")
    @app_commands.describe(
        game_system="The game system.",
        name="Name for the new season.",
    )
    @app_commands.autocomplete(game_system=game_system_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def start(
        self, interaction: discord.Interaction, game_system: str, name: str
    ) -> None:
        async with db_session_manager():
            await self._handle_start(interaction, game_system, name)

    # ── /wseason end ──────────────────────────────────────────────────────────

    @wseason_group.command(name="end", description="End the current wargame season.")
    @app_commands.describe(game_system="The game system.")
    @app_commands.autocomplete(game_system=game_system_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def end(
        self, interaction: discord.Interaction, game_system: str
    ) -> None:
        async with db_session_manager():
            await self._handle_end(interaction, game_system)

    # ── implementations ───────────────────────────────────────────────────────

    async def _handle_info(
        self,
        interaction: discord.Interaction,
        game_system: str,
        name: str | None,
    ) -> None:
        assert interaction.guild is not None
        from spellbot.services import WargameSeasonsService

        game_label = display_game(game_system)
        seasons_svc = WargameSeasonsService()

        if name is None:
            season = await seasons_svc.get_active(interaction.guild.id, game_system)
            if season is None:
                await interaction.response.send_message(
                    f"There is no active {game_label} season.", ephemeral=True
                )
                return
        else:
            season = await seasons_svc.get_by_name(interaction.guild.id, game_system, name)
            if season is None:
                await interaction.response.send_message(
                    f'No {game_label} season named "{name}" found.', ephemeral=True
                )
                return

        match_count = await seasons_svc.count_matches(season.id)
        start_ts = int(season.start_date.timestamp())
        end_ts = int(season.end_date.timestamp()) if season.end_date else None

        embed = discord.Embed(
            title=f"{game_label} Season — {season.name}",
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

    async def _handle_start(
        self,
        interaction: discord.Interaction,
        game_system: str,
        name: str,
    ) -> None:
        assert interaction.guild is not None
        from spellbot.services import WargameSeasonsService

        game_label = display_game(game_system)
        seasons_svc = WargameSeasonsService()

        active = await seasons_svc.get_active(interaction.guild.id, game_system)
        if active is not None:
            await interaction.response.send_message(
                f"There is already an active {game_label} season: **{active.name}**. "
                "End it first with `/wseason end`.",
                ephemeral=True,
            )
            return

        existing = await seasons_svc.get_by_name(interaction.guild.id, game_system, name)
        if existing is not None:
            await interaction.response.send_message(
                f'A {game_label} season named "{name}" already exists.', ephemeral=True
            )
            return

        season = await seasons_svc.create(interaction.guild.id, game_system, name)
        start_ts = int(season.start_date.timestamp())
        await interaction.response.send_message(
            f'✅ {game_label} season **{name}** has started! (<t:{start_ts}:F>)',
            ephemeral=False,
        )

    async def _handle_end(
        self,
        interaction: discord.Interaction,
        game_system: str,
    ) -> None:
        assert interaction.guild is not None
        from spellbot.services import WargameSeasonsService

        game_label = display_game(game_system)
        seasons_svc = WargameSeasonsService()
        ended = await seasons_svc.end_active(interaction.guild.id, game_system)
        if ended is None:
            await interaction.response.send_message(
                f"There is no active {game_label} season to end.", ephemeral=True
            )
            return

        await interaction.response.send_message(
            f'✅ {game_label} season **{ended.name}** has ended. '
            "Use `/wleaderboard` to see final standings.",
            ephemeral=False,
        )


async def setup(bot: SpellBot) -> None:  # pragma: no cover
    await bot.add_cog(WSeasonCog(bot), guild=settings.GUILD_OBJECT)
