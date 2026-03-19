from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import ui

from spellbot.database import db_session_manager

if TYPE_CHECKING:
    from spellbot import SpellBot

logger = logging.getLogger(__name__)


class WargameMatchView(discord.ui.View):
    """Persistent confirmation view for 1v1 wargame matches.

    Uses separate custom_ids from the EDH LeagueMatchView so both can coexist.
    Buttons: ✅ Confirm | ⚠️ Dispute | ❌ Cancel
    """

    def __init__(self, bot: SpellBot) -> None:
        super().__init__(timeout=None)
        self.bot = bot

    @ui.button(
        custom_id="wargame_match_confirm",
        label="Confirm",
        emoji="✅",
        style=discord.ButtonStyle.success,
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: ui.Button[WargameMatchView],
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        async with db_session_manager():
            await self._handle_confirm(interaction)

    @ui.button(
        custom_id="wargame_match_dispute",
        label="Dispute",
        emoji="⚠️",
        style=discord.ButtonStyle.danger,
    )
    async def dispute(
        self,
        interaction: discord.Interaction,
        button: ui.Button[WargameMatchView],
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        async with db_session_manager():
            await self._handle_dispute(interaction)

    @ui.button(
        custom_id="wargame_match_cancel",
        label="Cancel",
        emoji="❌",
        style=discord.ButtonStyle.secondary,
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: ui.Button[WargameMatchView],
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        async with db_session_manager():
            await self._handle_cancel(interaction)

    # ── helpers ──────────────────────────────────────────────────────────────

    async def _get_match(self, message_xid: int):  # type: ignore[return]
        from spellbot.services import WargameMatchesService

        svc = WargameMatchesService()
        return await svc.get_by_message_xid(message_xid)

    async def _handle_confirm(self, interaction: discord.Interaction) -> None:
        assert interaction.message is not None
        match = await self._get_match(interaction.message.id)

        if match is None:
            await interaction.followup.send("Match not found.", ephemeral=True)
            return

        player = next((p for p in match.players if p.user_xid == interaction.user.id), None)
        if player is None:
            await interaction.followup.send("You are not part of this match.", ephemeral=True)
            return
        if player.confirmed:
            await interaction.followup.send(
                "You have already confirmed this match.", ephemeral=True
            )
            return

        from spellbot.services import WargameMatchesService

        svc = WargameMatchesService()
        _already, all_confirmed = await svc.confirm_player(match, interaction.user.id)

        await self._refresh_embed(interaction, match)

        if all_confirmed:
            mentions = " ".join(f"<@{p.user_xid}>" for p in match.players)
            await interaction.followup.send(
                f"{mentions}\nThe match has been confirmed! ✅", ephemeral=False
            )
            for child in self.children:
                child.disabled = True  # type: ignore[attr-defined]
            try:
                await interaction.message.edit(view=self)
            except Exception:
                pass
            # Apply ELO and send DM summaries to each player
            elo_results = await self._apply_elo(match)
            await self._send_confirmation_dms(interaction, match, elo_results)
        else:
            await interaction.followup.send("You have confirmed the match.", ephemeral=True)

    async def _handle_dispute(self, interaction: discord.Interaction) -> None:
        assert interaction.message is not None
        assert interaction.guild is not None
        match = await self._get_match(interaction.message.id)

        if match is None:
            await interaction.followup.send("Match not found.", ephemeral=True)
            return

        player = next((p for p in match.players if p.user_xid == interaction.user.id), None)
        if player is None:
            await interaction.followup.send("You are not part of this match.", ephemeral=True)
            return

        if match.dispute_thread_xid is not None:
            await interaction.followup.send(
                f"This match has already been disputed in <#{match.dispute_thread_xid}>.",
                ephemeral=True,
            )
            return

        thread = await interaction.message.create_thread(name="Wargame Match Dispute")

        from spellbot.services import WargameConfigService, WargameMatchesService

        svc = WargameMatchesService()
        await svc.set_dispute_thread(match, thread.id)

        for p in match.players:
            try:
                member = await interaction.guild.fetch_member(p.user_xid)
                await thread.add_user(member)
            except Exception:
                pass

        cfg_svc = WargameConfigService()
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
        await interaction.followup.send("Dispute thread created.", ephemeral=True)

    async def _handle_cancel(self, interaction: discord.Interaction) -> None:
        assert interaction.message is not None
        match = await self._get_match(interaction.message.id)

        if match is None:
            await interaction.followup.send("Match not found.", ephemeral=True)
            return

        logger_player = match.players[0] if match.players else None
        if logger_player is None or logger_player.user_xid != interaction.user.id:
            await interaction.followup.send(
                "Only the player who logged this match can cancel it.", ephemeral=True
            )
            return

        dispute_thread_xid = match.dispute_thread_xid
        channel_xid = match.channel_xid
        message_xid = match.message_xid

        from spellbot.services import WargameMatchesService

        svc = WargameMatchesService()
        await svc.delete(match)

        if dispute_thread_xid:
            try:
                ch = self.bot.get_channel(dispute_thread_xid)
                if ch:
                    await ch.delete()  # type: ignore[union-attr]
            except Exception:
                pass

        if channel_xid and message_xid:
            try:
                ch = self.bot.get_channel(channel_xid)
                if ch and hasattr(ch, "fetch_message"):
                    msg = await ch.fetch_message(message_xid)  # type: ignore[union-attr]
                    await msg.delete()
            except Exception:
                pass

        await interaction.followup.send("The match has been cancelled.", ephemeral=True)

    async def _apply_elo(self, match) -> dict[int, tuple[int, int, int]]:
        """Apply ELO deltas for a confirmed wargame match.

        Returns {user_xid: (delta, old_elo, new_elo)}.
        Game system is inferred from the match's season.
        """
        try:
            from spellbot.services import WargameEloService
            from spellbot.services.wargame_seasons import WargameSeasonsService  # type: ignore[import]
            from spellbot.database import DatabaseSession
            from spellbot.models import WargameSeason

            # Load season to get the game_system slug
            season = DatabaseSession.get(WargameSeason, match.season_id)
            if season is None:
                return {}

            elo_svc = WargameEloService()
            player_xids = [p.user_xid for p in match.players]
            return await elo_svc.update_for_match(
                guild_xid=match.guild_xid,
                player_xids=player_xids,
                game_system=season.game_system,
                winner_xid=match.winner_xid,
            )
        except Exception as exc:
            logger.warning("Failed to apply wargame ELO for match %s: %s", match.id, exc)
            return {}

    async def _send_confirmation_dms(
        self,
        interaction: discord.Interaction,
        match,
        elo_results: dict[int, tuple[int, int, int]] | None = None,
    ) -> None:
        """DM each player a brief summary of the confirmed match, including ELO change."""
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
                title="⚔️ Wargame Match Confirmed",
                description=(
                    f"Match **#{match.id}** has been confirmed by all players."
                ),
                color=discord.Color.green(),
            )
            embed.add_field(name="Result", value=result, inline=True)
            embed.add_field(name="Opponent(s)", value=opponent_str, inline=True)

            # ELO change field
            if elo_results and player.user_xid in elo_results:
                delta, old_elo, new_elo = elo_results[player.user_xid]
                arrow = "📈" if delta >= 0 else "📉"
                sign = "+" if delta >= 0 else ""
                elo_text = f"{arrow} {sign}{delta} → **{new_elo}** ELO *(was {old_elo})*"
                embed.add_field(name="🎯 ELO Change", value=elo_text, inline=False)

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
        assert interaction.message is not None
        try:
            embeds = interaction.message.embeds
            if not embeds:
                return
            embed = embeds[0].copy()
            confirmed = [p for p in match.players if p.confirmed]
            new_value = (
                "The following players have confirmed: "
                + ", ".join(f"<@{p.user_xid}>" for p in confirmed)
                if confirmed
                else "Nobody has confirmed this match yet."
            )
            fields = list(embed.fields)
            if fields:
                embed.remove_field(len(fields) - 1)
                embed.add_field(name="Confirmed", value=new_value, inline=False)
            await interaction.message.edit(embeds=[embed])
        except Exception as exc:
            logger.warning("Failed to refresh wargame match embed: %s", exc)
