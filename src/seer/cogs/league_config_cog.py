from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from seer.database import db_session_manager
from seer.settings import settings
from seer.utils import for_all_callbacks, is_guild

if TYPE_CHECKING:
    from seer import Seer

logger = logging.getLogger(__name__)


@for_all_callbacks(app_commands.check(is_guild))
class LeagueConfigCog(commands.Cog):
    def __init__(self, bot: Seer) -> None:
        self.bot = bot

    lc_group = app_commands.Group(
        name="leagueconfig",
        description="Configure league settings for this server.",
        default_permissions=discord.Permissions(manage_guild=True),
    )

    # ── /leagueconfig minimum-games ───────────────────────────────────────────

    @lc_group.command(
        name="minimum-games",
        description="Minimum confirmed games required to appear on the leaderboard.",
    )
    @app_commands.describe(amount="Number of games required (leave blank to view current).")
    async def minimum_games(
        self, interaction: discord.Interaction, amount: int | None = None
    ) -> None:
        async with db_session_manager():
            await self._update(interaction, "minimum_games", amount, "Minimum games")

    # ── /leagueconfig points-gained ───────────────────────────────────────────

    @lc_group.command(name="points-gained", description="Points awarded per match win.")
    @app_commands.describe(amount="Points per win (leave blank to view current).")
    async def points_gained(
        self, interaction: discord.Interaction, amount: int | None = None
    ) -> None:
        async with db_session_manager():
            await self._update(interaction, "points_gained", amount, "Points per win")

    # ── /leagueconfig points-lost ─────────────────────────────────────────────

    @lc_group.command(name="points-lost", description="Points deducted per match loss.")
    @app_commands.describe(amount="Points per loss (leave blank to view current).")
    async def points_lost(
        self, interaction: discord.Interaction, amount: int | None = None
    ) -> None:
        async with db_session_manager():
            await self._update(interaction, "points_lost", amount, "Points per loss")

    # ── /leagueconfig points-per-draw ─────────────────────────────────────────

    @lc_group.command(name="points-per-draw", description="Points awarded per draw.")
    @app_commands.describe(amount="Points per draw (leave blank to view current).")
    async def points_per_draw(
        self, interaction: discord.Interaction, amount: int | None = None
    ) -> None:
        async with db_session_manager():
            await self._update(interaction, "points_per_draw", amount, "Points per draw")

    # ── /leagueconfig base-points ─────────────────────────────────────────────

    @lc_group.command(
        name="base-points",
        description="Offset added to all displayed point totals.",
    )
    @app_commands.describe(amount="Base point offset (leave blank to view current).")
    async def base_points(
        self, interaction: discord.Interaction, amount: int | None = None
    ) -> None:
        async with db_session_manager():
            await self._update(interaction, "base_points", amount, "Base points")

    # ── /leagueconfig deck-limit ──────────────────────────────────────────────

    @lc_group.command(name="deck-limit", description="Maximum decks a player can register.")
    @app_commands.describe(amount="Deck limit (leave blank to view current).")
    async def deck_limit(
        self, interaction: discord.Interaction, amount: int | None = None
    ) -> None:
        async with db_session_manager():
            await self._update(interaction, "deck_limit", amount, "Deck limit")

    # ── /leagueconfig enable-draws ────────────────────────────────────────────

    @lc_group.command(name="enable-draws", description="Allow or disallow draw logging.")
    @app_commands.describe(enabled="True to allow draws, False to disable (leave blank to view).")
    async def enable_draws(
        self, interaction: discord.Interaction, enabled: bool | None = None
    ) -> None:
        async with db_session_manager():
            assert interaction.guild is not None
            from seer.services import LeagueConfigService

            svc = LeagueConfigService()
            if enabled is not None:
                config = await svc.update(interaction.guild.id, enable_draws=enabled)
            else:
                config = await svc.upsert(interaction.guild.id)

            status = "enabled" if config.enable_draws else "disabled"
            verb = "is now" if enabled is not None else "is currently"
            await interaction.response.send_message(
                f"Draws {verb} **{status}**.", ephemeral=True
            )

    # ── /leagueconfig dispute-role ────────────────────────────────────────────

    @lc_group.command(
        name="dispute-role",
        description="Set or clear the role added to dispute threads.",
    )
    @app_commands.describe(
        role="Role to add to dispute threads.",
        unset="Set to True to remove the dispute role.",
    )
    async def dispute_role(
        self,
        interaction: discord.Interaction,
        role: discord.Role | None = None,
        unset: bool = False,
    ) -> None:
        async with db_session_manager():
            assert interaction.guild is not None
            from seer.services import LeagueConfigService

            svc = LeagueConfigService()
            if unset:
                config = await svc.update(interaction.guild.id, dispute_role_xid=None)
                await interaction.response.send_message(
                    "Dispute role has been cleared.", ephemeral=True
                )
            elif role is not None:
                config = await svc.update(interaction.guild.id, dispute_role_xid=role.id)
                await interaction.response.send_message(
                    f"Dispute role is now {role.mention}.", ephemeral=True
                )
            else:
                config = await svc.upsert(interaction.guild.id)
                if config.dispute_role_xid:
                    await interaction.response.send_message(
                        f"Dispute role is currently <@&{config.dispute_role_xid}>.",
                        ephemeral=True,
                    )
                else:
                    await interaction.response.send_message(
                        "No dispute role is currently set.", ephemeral=True
                    )

    # ── generic helper ────────────────────────────────────────────────────────

    async def _update(
        self,
        interaction: discord.Interaction,
        field: str,
        value: int | None,
        label: str,
    ) -> None:
        assert interaction.guild is not None
        from seer.services import LeagueConfigService

        svc = LeagueConfigService()
        if value is not None:
            if value < 0:
                await interaction.response.send_message(
                    "Value must be 0 or greater.", ephemeral=True
                )
                return
            config = await svc.update(interaction.guild.id, **{field: value})
        else:
            config = await svc.upsert(interaction.guild.id)

        current = getattr(config, field)
        verb = "is now" if value is not None else "is currently"
        await interaction.response.send_message(
            f"{label} {verb} **{current}**.", ephemeral=True
        )


async def setup(bot: Seer) -> None:  # pragma: no cover
    await bot.add_cog(LeagueConfigCog(bot), guild=settings.GUILD_OBJECT)
