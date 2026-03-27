from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING
from uuid import uuid4

import discord
from cachetools import TTLCache
from ddtrace.trace import tracer
from discord.ext.commands import AutoShardedBot, CommandError, CommandNotFound, Context

from .database import db_session_manager, initialize_connection
from .enums import GameService
from .integrations import convoke, spelltable, tablestream
from .metrics import setup_ignored_errors, setup_metrics
from .models import GameLinkDetails
from .operations import safe_delete_message
from .services import ServicesRegistry
from .settings import settings
from .utils import user_can_moderate

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from .models import GameDict


logger = logging.getLogger(__name__)

# Disable pointless nacl warning log coming from discord.py.
if hasattr(discord.VoiceClient, "warn_nacl"):  # pragma: no cover
    discord.VoiceClient.warn_nacl = False


class Seer(AutoShardedBot):
    def __init__(
        self,
        mock_games: bool = False,
        create_connection: bool = True,
    ) -> None:
        intents = discord.Intents().default()
        intents.members = True
        intents.message_content = True
        intents.messages = True
        logger.info("intents.value: %s", intents.value)
        kwargs = {}
        if settings.BOT_APPLICATION_ID is not None:
            kwargs["application_id"] = int(settings.BOT_APPLICATION_ID)
        super().__init__(command_prefix="!", help_command=None, intents=intents, **kwargs)
        self.mock_games = mock_games
        self.create_connection = create_connection
        self.guild_locks = TTLCache[int, asyncio.Lock](maxsize=100, ttl=3600)  # 1 hr
        self.supporters: set[int] = set()

    async def on_ready(self) -> None:  # pragma: no cover
        logger.info("client ready")

    async def on_shard_ready(self, shard_id: int) -> None:  # pragma: no cover
        logger.info("shard %s ready", shard_id)

    async def setup_hook(self) -> None:  # pragma: no cover
        # Note: In tests we create the connection using fixtures.
        if self.create_connection:  # pragma: no cover
            logger.info("initializing database connection...")
            await initialize_connection("seer-bot")

        # register persistent views
        from .views import GameView, SetupView

        self.add_view(GameView(self))
        self.add_view(SetupView(self))
        from .views import LeagueMatchView, MagicMatchView, WargameMatchView, ShopView
        self.add_view(LeagueMatchView(self))
        self.add_view(WargameMatchView(self))
        self.add_view(MagicMatchView(self))
        self.add_view(ShopView(self))

        # Load all cog extensions (commands register locally in the tree)
        from .utils import load_extensions

        await load_extensions(self, do_sync=False)

        # Sync commands to Discord in the background so setup_hook
        # completes immediately and the bot goes online right away.
        # If rate-limited, the bot stays online while it waits.
        import os
        skip_sync = os.getenv("SKIP_COMMAND_SYNC", "").lower() in ("1", "true", "yes")
        if skip_sync:
            logger.info("SKIP_COMMAND_SYNC is set — skipping command sync")
        else:
            self.loop.create_task(self._background_sync())

    async def _background_sync(self) -> None:  # pragma: no cover
        """Sync slash commands in the background so the bot stays online.

        If rate-limited, waits ONE cooldown and retries once. If still
        rate-limited after that, gives up so we don't spiral into an
        ever-growing 429 loop.
        """
        await self.wait_until_ready()
        guild = settings.GUILD_OBJECT
        if guild:
            logger.info("background sync: syncing commands to guild %s", guild.id)
        else:
            logger.info("background sync: syncing global commands")

        for attempt in range(2):  # at most 2 attempts
            try:
                await self.tree.sync(guild=guild)
                logger.info("background sync: command sync complete")
                return
            except discord.HTTPException as e:
                if e.status == 429 and attempt == 0:
                    retry_after = getattr(e, "retry_after", 300) or 300
                    logger.warning(
                        "background sync: rate limited, waiting %.0fs then retrying once",
                        retry_after,
                    )
                    await asyncio.sleep(retry_after)
                else:
                    logger.error("background sync failed (attempt %d): %s", attempt + 1, e)
                    return
            except Exception as e:
                logger.error("background sync failed: %s", e)
                return

    @asynccontextmanager
    async def guild_lock(self, guild_xid: int) -> AsyncGenerator[None, None]:
        if not self.guild_locks.get(guild_xid):
            self.guild_locks[guild_xid] = asyncio.Lock()
        async with self.guild_locks[guild_xid]:
            yield

    @tracer.wrap()
    async def create_game_link(self, game: GameDict) -> GameLinkDetails:
        if self.mock_games:
            return GameLinkDetails(f"http://exmaple.com/game/{uuid4()}")
        service = game.get("service")
        if span := tracer.current_span():
            span.set_tag("link_service", GameService(service).name)
        match service:
            case GameService.SPELLTABLE.value:
                link = await spelltable.generate_link(game)
                return GameLinkDetails(link)
            case GameService.CONVOKE.value:
                details = await convoke.generate_link(game)
                return GameLinkDetails(*details)
            case GameService.TABLE_STREAM.value:
                details = await tablestream.generate_link(game)
                return GameLinkDetails(*details)
            case _:
                return GameLinkDetails()

    @tracer.wrap(name="interaction", resource="on_message")
    async def on_message(
        self,
        message: discord.Message,
    ) -> None:
        span = tracer.current_span()
        if span:  # pragma: no cover
            setup_ignored_errors(span)

        # handle DMs normally
        if not message.guild or not hasattr(message.guild, "id"):
            return await super().on_message(message)
        if span:  # pragma: no cover
            span.set_tag("guild_id", str(message.guild.id))

        # ignore everything except messages in text channels
        if not hasattr(message.channel, "type") or message.channel.type != discord.ChannelType.text:
            return None
        if span:  # pragma: no cover
            span.set_tag("channel_id", str(message.channel.id))

        # ignore hidden/ephemeral messages
        if message.flags.value & 64:
            return None

        # to verify users we need their user id
        if not hasattr(message.author, "id"):
            return None

        message_author_xid = message.author.id
        if span:
            span.set_tag("author_id", str(message_author_xid))

        # don't try to verify the bot itself
        if self.user and message_author_xid == self.user.id:  # pragma: no cover
            return None

        async with db_session_manager():
            await self.handle_verification(message)
            return None

    @tracer.wrap(name="interaction", resource="on_message_delete")
    async def on_message_delete(self, message: discord.Message) -> None:
        message_xid: int | None = getattr(message, "id", None)
        if not message_xid:
            return
        async with db_session_manager():
            await self.handle_message_deleted(message)

    async def on_command_error(
        self,
        context: Context[Seer],
        exception: CommandError,
    ) -> None:
        if isinstance(exception, CommandNotFound):
            return None
        return await super().on_command_error(context, exception)

    @tracer.wrap()
    async def handle_verification(self, message: discord.Message) -> None:
        services = ServicesRegistry()
        message_author_xid = message.author.id
        verified: bool | None = None
        assert message.guild is not None
        await services.guilds.upsert(message.guild)
        channel_data = await services.channels.upsert(message.channel)
        if channel_data["auto_verify"]:
            verified = True
        assert message.guild
        guild: discord.Guild = message.guild
        await services.verifies.upsert(guild.id, message_author_xid, verified)
        if not user_can_moderate(message.author, guild, message.channel):
            user_is_verified = await services.verifies.is_verified()
            if user_is_verified and channel_data["unverified_only"]:
                await safe_delete_message(message)
            if not user_is_verified and channel_data["verified_only"]:
                await safe_delete_message(message)

    @tracer.wrap()
    async def handle_message_deleted(self, message: discord.Message) -> None:
        services = ServicesRegistry()
        data = await services.games.select_by_message_xid(message.id)
        if not data:
            return
        game_id = data["id"]
        logger.info("Game %s was deleted manually.", game_id)
        if not data["started_at"]:  # someone deleted a pending game
            await services.games.delete_games([game_id])


def build_bot(
    mock_games: bool = False,
    create_connection: bool = True,
) -> Seer:
    bot = Seer(
        mock_games=mock_games,
        create_connection=create_connection,
    )
    setup_metrics()
    return bot
