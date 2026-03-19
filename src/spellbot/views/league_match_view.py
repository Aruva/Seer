from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import ui

from spellbot.database import db_session_manager

if TYPE_CHECKING:
    from spellbot import SpellBot

logger = logging.getLogger(__name__)


class LeagueMatchView(discord.ui.View):
    """Persistent view attached to a match confirmation embed.

    Buttons:
    - ✅ Confirm  – a player confirms the match result
    - ⚠️ Dispute  – a player disputes; creates a thread
    - ❌ Cancel   – the match logger cancels the match
    """

    def __init__(self, bot: SpellBot) -> None:
        super().__init__(timeout=None)
        self.bot = bot

    @ui.button(
        custom_id="league_match_confirm",
        label="Confirm",
        emoji="✅",
        style=discord.ButtonStyle.success,
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: ui.Button[LeagueMatchView],
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        async with db_session_manager():
            await self._handle_confirm(interaction)

    @ui.button(
        custom_id="league_match_dispute",
        label="Dispute",
        emoji="⚠️",
        style=discord.ButtonStyle.danger,
    )
    async def dispute(
        self,
        interaction: discord.Interaction,
        button: ui.Button[LeagueMatchView],
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        async with db_session_manager():
            await self._handle_dispute(interaction)

    @ui.button(
        custom_id="league_match_cancel",
        label="Cancel",
        emoji="❌",
        style=discord.ButtonStyle.secondary,
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: ui.Button[LeagueMatchView],
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        async with db_session_manager():
            await self._handle_cancel(interaction)

    # ── helpers ──────────────────────────────────────────────────────────────

    async def _get_match_from_message(self, message_xid: int):  # type: ignore[return]
        from spellbot.models import LeagueMatch

        from spellbot.database import DatabaseSession

        return (
            DatabaseSession.query(LeagueMatch)
            .filter(LeagueMatch.message_xid == message_xid)
            .one_or_none()
        )

    async def _handle_confirm(self, interaction: discord.Interaction) -> None:
        assert interaction.message is not None
        match = await self._get_match_from_message(interaction.message.id)  # type: ignore[arg-type]

        if match is None:
            await interaction.followup.send("Match not found.", ephemeral=True)
            return

        player = next(
            (p for p in match.players if p.user_xid == interaction.user.id), None
        )
        if player is None:
            await interaction.followup.send(
                "You are not part of this match.", ephemeral=True
            )
            return

        if player.confirmed:
            await interaction.followup.send(
                "You have already confirmed this match.", ephemeral=True
            )
            return

        from spellbot.services import LeagueMatchesService

        svc = LeagueMatchesService()
        _already, all_confirmed = await svc.confirm_player(match, interaction.user.id)

        # Update the embed's confirmed field
        await self._refresh_embed(interaction, match)

        if all_confirmed:
            mentions = " ".join(f"<@{p.user_xid}>" for p in match.players)
            await interaction.followup.send(
                f"{mentions}\nThe match has been confirmed by all players! ✅",
                ephemeral=False,
            )
            # Disable all buttons now that the match is fully confirmed
            for child in self.children:
                child.disabled = True  # type: ignore[attr-defined]
            try:
                await interaction.message.edit(view=self)  # type: ignore[union-attr]
            except Exception:
                pass
            # Apply ELO updates and send DM summary to each player.
            # Retrieve stored seat positions (may be None for untracked games).
            player_xids = [p.user_xid for p in match.players]
            seat_positions: dict[int, int] | None = None
            if all(p.seat is not None for p in match.players):
                seat_positions = {p.user_xid: p.seat for p in match.players}  # type: ignore[misc]

            from spellbot.services.league_elo import LeagueEloService

            elo_svc = LeagueEloService()
            elo_results = await elo_svc.update_for_match(
                match.guild_xid, match.winner_xid, player_xids, seat_positions
            )
            await self._send_confirmation_dms(interaction, match, elo_results, seat_positions)
        else:
            await interaction.followup.send(
                "You have confirmed the match.", ephemeral=True
            )

    async def _handle_dispute(self, interaction: discord.Interaction) -> None:
        assert interaction.message is not None
        assert interaction.guild is not None
        match = await self._get_match_from_message(interaction.message.id)  # type: ignore[arg-type]

        if match is None:
            await interaction.followup.send("Match not found.", ephemeral=True)
            return

        player = next(
            (p for p in match.players if p.user_xid == interaction.user.id), None
        )
        if player is None:
            await interaction.followup.send(
                "You are not part of this match.", ephemeral=True
            )
            return

        if match.dispute_thread_xid is not None:
            await interaction.followup.send(
                f"This match has already been disputed in <#{match.dispute_thread_xid}>.",
                ephemeral=True,
            )
            return

        if not interaction.message.channel.permissions_for(interaction.guild.me).create_public_threads:  # type: ignore[union-attr]
            await interaction.followup.send(
                "I don't have permission to create threads in this channel.", ephemeral=True
            )
            return

        thread = await interaction.message.create_thread(name="Match Dispute")

        from spellbot.services import LeagueMatchesService

        svc = LeagueMatchesService()
        await svc.set_dispute_thread(match, thread.id)

        # Add all players to the thread
        for p in match.players:
            try:
                await thread.add_user(
                    await interaction.guild.fetch_member(p.user_xid)
                )
            except Exception:
                pass

        # Add dispute role members if configured
        from spellbot.services import LeagueConfigService

        cfg_svc = LeagueConfigService()
        config = await cfg_svc.upsert(interaction.guild.id)
        if config.dispute_role_xid:
            role = interaction.guild.get_role(config.dispute_role_xid)
            if role:
                for member in role.members:
                    try:
                        await thread.add_user(member)
                    except Exception:
                        pass

        await thread.send(
            f"<@{interaction.user.id}>, please explain your reasoning for disputing this match."
        )
        await interaction.followup.send(
            "The match dispute thread has been created.", ephemeral=True
        )

    async def _handle_cancel(self, interaction: discord.Interaction) -> None:
        assert interaction.message is not None
        match = await self._get_match_from_message(interaction.message.id)  # type: ignore[arg-type]

        if match is None:
            await interaction.followup.send("Match not found.", ephemeral=True)
            return

        # Only the player who logged the match (first in the list) can cancel
        logger_player = match.players[0] if match.players else None
        if logger_player is None or logger_player.user_xid != interaction.user.id:
            await interaction.followup.send(
                "Only the player who logged this match can cancel it.", ephemeral=True
            )
            return

        dispute_thread_xid = match.dispute_thread_xid
        channel_xid = match.channel_xid
        message_xid = match.message_xid

        from spellbot.services import LeagueMatchesService

        svc = LeagueMatchesService()
        await svc.delete(match)

        # Delete dispute thread if any
        if dispute_thread_xid:
            try:
                ch = self.bot.get_channel(dispute_thread_xid)
                if ch:
                    await ch.delete()  # type: ignore[union-attr]
            except Exception:
                pass

        # Delete the confirmation message
        if channel_xid and message_xid:
            try:
                ch = self.bot.get_channel(channel_xid)
                if ch and hasattr(ch, "fetch_message"):
                    msg = await ch.fetch_message(message_xid)  # type: ignore[union-attr]
                    await msg.delete()
            except Exception:
                pass

        await interaction.followup.send("The match has been cancelled.", ephemeral=True)

    async def _send_confirmation_dms(
        self,
        interaction: discord.Interaction,
        match,
        elo_results: dict[int, dict[str, int]] | None = None,
        seat_positions: dict[int, int] | None = None,
    ) -> None:
        """DM each player a brief summary of the confirmed EDH match with ELO delta."""
        channel_link = (
            f"https://discord.com/channels/{match.guild_xid}/"
            f"{match.channel_xid}/{match.message_xid}"
            if match.channel_xid and match.message_xid
            else None
        )
        for player in match.players:
            if match.winner_xid is None:
                result = "🤝 Draw"
            elif match.winner_xid == player.user_xid:
                result = "🏆 Win"
            else:
                result = "❌ Loss"

            opponents = [p for p in match.players if p.user_xid != player.user_xid]
            opponent_str = ", ".join(f"<@{p.user_xid}>" for p in opponents)

            embed = discord.Embed(
                title="🃏 EDH Match Confirmed",
                description=f"Match **#{match.id}** has been confirmed by all players.",
                color=discord.Color.green(),
            )
            embed.add_field(name="Result", value=result, inline=True)
            embed.add_field(name="Other Players", value=opponent_str, inline=True)

            # Show ELO delta if we have it
            if elo_results and player.user_xid in elo_results:
                info = elo_results[player.user_xid]
                delta = info["delta"]
                new_elo = info["new"]
                sign = "+" if delta >= 0 else ""
                delta_emoji = "📈" if delta >= 0 else "📉"
                elo_value = f"**{sign}{delta}** → {new_elo}"
                # Note when seat correction was applied
                if seat_positions and player.user_xid in seat_positions:
                    s = seat_positions[player.user_xid]
                    elo_value += f"\n*(seat {s} correction applied)*"
                embed.add_field(
                    name=f"{delta_emoji} ELO",
                    value=elo_value,
                    inline=True,
                )

            if channel_link:
                embed.add_field(
                    name="Jump to match",
                    value=f"[View in Discord]({channel_link})",
                    inline=False,
                )
            embed.set_footer(text="SouthSeer — Southside Studio and Hobbies")

            try:
                user = await self.bot.fetch_user(player.user_xid)
                await user.send(embed=embed)
            except Exception:
                pass  # DMs may be disabled; silently skip

    async def _refresh_embed(self, interaction: discord.Interaction, match) -> None:  # type: ignore[return]
        """Update the 'Confirmed' field on the match embed."""
        assert interaction.message is not None
        try:
            embeds = interaction.message.embeds
            if not embeds:
                return
            embed = embeds[0].copy()
            confirmed = [p for p in match.players if p.confirmed]
            new_value = (
                f"The following players have confirmed: "
                + ", ".join(f"<@{p.user_xid}>" for p in confirmed)
                if confirmed
                else "Nobody has confirmed this match yet."
            )
            # The last field is always the "Confirmed" field
            fields = list(embed.fields)
            if fields:
                embed.remove_field(len(fields) - 1)
                embed.add_field(name="Confirmed", value=new_value, inline=False)
            await interaction.message.edit(embeds=[embed])
        except Exception as exc:
            logger.warning("Failed to refresh match embed: %s", exc)
