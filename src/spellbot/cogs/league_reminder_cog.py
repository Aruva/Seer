from __future__ import annotations

"""Scheduled task that reminds EDH league players who haven't confirmed a match."""

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from discord.ext import commands, tasks

from spellbot.database import db_session_manager
from spellbot.settings import settings

if TYPE_CHECKING:
    from spellbot import SpellBot

logger = logging.getLogger(__name__)

CHECK_INTERVAL_MINUTES = 30


class LeagueReminderCog(commands.Cog):
    """Periodically DMs league players who haven't confirmed a match result."""

    def __init__(self, bot: SpellBot) -> None:
        self.bot = bot

    def cog_load(self) -> None:  # pragma: no cover
        self.reminder_loop.start()

    def cog_unload(self) -> None:  # pragma: no cover
        self.reminder_loop.cancel()

    @tasks.loop(minutes=CHECK_INTERVAL_MINUTES)
    async def reminder_loop(self) -> None:  # pragma: no cover
        try:
            async with db_session_manager():
                await self._run_reminders()
        except Exception as exc:
            logger.exception("LeagueReminderCog reminder_loop error: %s", exc)

    @reminder_loop.before_loop
    async def before_reminder_loop(self) -> None:  # pragma: no cover
        await self.bot.wait_until_ready()

    async def _run_reminders(self) -> None:
        from spellbot.services import LeagueConfigService, LeagueMatchesService

        matches_svc = LeagueMatchesService()
        cfg_svc = LeagueConfigService()

        pending = await matches_svc.get_all_pending()
        now = datetime.now(UTC)

        # Cache per-guild reminder_hours so we don't re-query the same guild twice
        guilds_checked: dict[int, int] = {}

        for match in pending:
            guild_xid = match.guild_xid

            if guild_xid not in guilds_checked:
                config = await cfg_svc.upsert(guild_xid)
                guilds_checked[guild_xid] = config.reminder_hours

            reminder_hours = guilds_checked[guild_xid]
            if reminder_hours == 0:
                continue  # Reminders disabled for this guild

            match_age = now - match.created_at.replace(tzinfo=UTC)
            if match_age < timedelta(hours=reminder_hours):
                continue

            for player in match.players:
                if player.confirmed:
                    continue
                await self._send_reminder_dm(match, player.user_xid)

    async def _send_reminder_dm(self, match, user_xid: int) -> None:
        import discord

        channel_link = (
            f"https://discord.com/channels/{match.guild_xid}/"
            f"{match.channel_xid}/{match.message_xid}"
            if match.channel_xid and match.message_xid
            else None
        )

        embed = discord.Embed(
            title="⏰ Pending EDH Match Confirmation",
            description=(
                f"You have an EDH league match **#{match.id}** that is still waiting "
                "for your confirmation.\n\n"
                "Please return to the match and click **✅ Confirm** or **⚠️ Dispute**.\n\n"
                "*Until the match is confirmed, ELO ratings won't be updated.*"
            ),
            color=discord.Color.orange(),
        )
        if channel_link:
            embed.add_field(
                name="Go to match",
                value=f"[Click here]({channel_link})",
                inline=False,
            )
        embed.set_footer(text="SouthSeer — Southside Studio and Hobbies")

        try:
            user = await self.bot.fetch_user(user_xid)
            await user.send(embed=embed)
            logger.info(
                "Sent EDH league reminder to user %d for match #%d", user_xid, match.id
            )
        except Exception as exc:
            logger.debug(
                "Could not DM user %d for match #%d: %s", user_xid, match.id, exc
            )


async def setup(bot: SpellBot) -> None:  # pragma: no cover
    await bot.add_cog(LeagueReminderCog(bot), guild=settings.GUILD_OBJECT)
