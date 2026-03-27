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
class MatchCog(commands.Cog):
    def __init__(self, bot: Seer) -> None:
        self.bot = bot

    match_group = app_commands.Group(
        name="match",
        description="Manage logged matches.",
    )

    # ── /match pending ────────────────────────────────────────────────────────

    @match_group.command(name="pending", description="List pending (unconfirmed) matches.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def pending(self, interaction: discord.Interaction) -> None:
        async with db_session_manager():
            await self._handle_pending(interaction)

    # ── /match disputed ───────────────────────────────────────────────────────

    @match_group.command(name="disputed", description="List disputed matches.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def disputed(self, interaction: discord.Interaction) -> None:
        async with db_session_manager():
            await self._handle_disputed(interaction)

    # ── /match accept ─────────────────────────────────────────────────────────

    @match_group.command(name="accept", description="Admin-accept a match by ID.")
    @app_commands.describe(match_id="ID of the match to accept.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def accept(self, interaction: discord.Interaction, match_id: int) -> None:
        async with db_session_manager():
            await self._handle_accept(interaction, match_id)

    # ── /match delete ─────────────────────────────────────────────────────────

    @match_group.command(name="delete", description="Delete a match by ID.")
    @app_commands.describe(match_id="ID of the match to delete.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def delete(self, interaction: discord.Interaction, match_id: int) -> None:
        async with db_session_manager():
            await self._handle_delete(interaction, match_id)

    # ── /match list ───────────────────────────────────────────────────────────

    @match_group.command(name="list", description="View your match history.")
    @app_commands.describe(
        deck="Filter by deck name.",
        season="Filter by season name.",
    )
    async def list_matches(
        self,
        interaction: discord.Interaction,
        deck: str | None = None,
        season: str | None = None,
    ) -> None:
        async with db_session_manager():
            await self._handle_list(interaction, deck, season)

    # ── implementations ───────────────────────────────────────────────────────

    async def _handle_pending(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None
        from seer.services import LeagueMatchesService, LeagueSeasonsService

        seasons_svc = LeagueSeasonsService()
        active = await seasons_svc.get_active(interaction.guild.id)
        if active is None:
            await interaction.response.send_message("There is no active season.", ephemeral=True)
            return

        matches_svc = LeagueMatchesService()
        matches = await matches_svc.get_pending(interaction.guild.id, active.id)
        if not matches:
            await interaction.response.send_message("There are no pending matches.", ephemeral=True)
            return

        embed = discord.Embed(
            title="Pending Matches",
            description="These matches have not yet been confirmed by all players.",
            color=discord.Color.blue(),
        )
        for m in matches[:10]:
            players_str = ", ".join(f"<@{p.user_xid}>" for p in m.players)
            confirmed_count = sum(1 for p in m.players if p.confirmed)
            embed.add_field(
                name=f"Match #{m.id}",
                value=f"{players_str}\nConfirmed: {confirmed_count}/{len(m.players)}",
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _handle_disputed(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None
        from seer.services import LeagueMatchesService, LeagueSeasonsService

        seasons_svc = LeagueSeasonsService()
        active = await seasons_svc.get_active(interaction.guild.id)
        if active is None:
            await interaction.response.send_message("There is no active season.", ephemeral=True)
            return

        matches_svc = LeagueMatchesService()
        matches = await matches_svc.get_disputed(interaction.guild.id, active.id)
        if not matches:
            await interaction.response.send_message("There are no disputed matches.", ephemeral=True)
            return

        embed = discord.Embed(
            title="Disputed Matches",
            description="These matches have open dispute threads.",
            color=discord.Color.orange(),
        )
        for m in matches[:10]:
            players_str = ", ".join(f"<@{p.user_xid}>" for p in m.players)
            thread_str = f" — <#{m.dispute_thread_xid}>" if m.dispute_thread_xid else ""
            embed.add_field(
                name=f"Match #{m.id}",
                value=f"{players_str}{thread_str}",
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _handle_accept(self, interaction: discord.Interaction, match_id: int) -> None:
        assert interaction.guild is not None
        from seer.services import LeagueMatchesService

        svc = LeagueMatchesService()
        match = await svc.get_by_id(match_id)
        if match is None or match.guild_xid != interaction.guild.id:
            await interaction.response.send_message(
                "No match found with that ID on this server.", ephemeral=True
            )
            return

        confirmed = await svc.admin_confirm(match)
        if not confirmed:
            await interaction.response.send_message(
                "That match has already been confirmed.", ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"Match #{match_id} has been confirmed.", ephemeral=True
        )

    async def _handle_delete(self, interaction: discord.Interaction, match_id: int) -> None:
        assert interaction.guild is not None
        from seer.services import LeagueMatchesService

        svc = LeagueMatchesService()
        match = await svc.get_by_id(match_id)
        if match is None or match.guild_xid != interaction.guild.id:
            await interaction.response.send_message(
                "No match found with that ID on this server.", ephemeral=True
            )
            return

        dispute_thread_xid = match.dispute_thread_xid
        channel_xid = match.channel_xid
        message_xid = match.message_xid

        await svc.delete(match)

        # Clean up dispute thread
        if dispute_thread_xid:
            ch = self.bot.get_channel(dispute_thread_xid)
            if ch:
                try:
                    await ch.delete()  # type: ignore[union-attr]
                except Exception:
                    pass

        # Clean up confirmation message
        if channel_xid and message_xid:
            ch = self.bot.get_channel(channel_xid)
            if ch and hasattr(ch, "fetch_message"):
                try:
                    msg = await ch.fetch_message(message_xid)  # type: ignore[union-attr]
                    await msg.delete()
                except Exception:
                    pass

        await interaction.response.send_message(
            f"Match #{match_id} has been deleted.", ephemeral=True
        )

    async def _handle_list(
        self,
        interaction: discord.Interaction,
        deck_name: str | None,
        season_name: str | None,
    ) -> None:
        assert interaction.guild is not None
        from seer.services import LeagueDecksService, LeagueMatchesService, LeagueSeasonsService

        deck_id: int | None = None
        if deck_name:
            deck_svc = LeagueDecksService()
            deck = await deck_svc.get_by_name(interaction.guild.id, interaction.user.id, deck_name)
            if deck is None:
                await interaction.response.send_message(
                    f'You have no deck named "{deck_name}".', ephemeral=True
                )
                return
            deck_id = deck.id

        season_id: int | None = None
        if season_name:
            seasons_svc = LeagueSeasonsService()
            season = await seasons_svc.get_by_name(interaction.guild.id, season_name)
            if season is None:
                await interaction.response.send_message(
                    f'No season named "{season_name}" found.', ephemeral=True
                )
                return
            season_id = season.id

        matches_svc = LeagueMatchesService()
        matches = await matches_svc.get_for_user(
            interaction.guild.id,
            interaction.user.id,
            season_id=season_id,
            deck_id=deck_id,
        )

        if not matches:
            await interaction.response.send_message(
                "You have no confirmed matches with those filters.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="Your Matches",
            description=f"Showing your last {min(len(matches), 10)} confirmed match(es).",
            color=discord.Color.blue(),
        )
        for m in matches[:10]:
            result = (
                "🏆 Win"
                if m.winner_xid == interaction.user.id
                else ("🤝 Draw" if m.winner_xid is None else "❌ Loss")
            )
            players_str = ", ".join(f"<@{p.user_xid}>" for p in m.players)
            embed.add_field(
                name=f"Match #{m.id} — {result}",
                value=players_str,
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: Seer) -> None:  # pragma: no cover
    await bot.add_cog(MatchCog(bot), guild=settings.GUILD_OBJECT)
