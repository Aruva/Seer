from __future__ import annotations

import logging
from importlib import import_module
from inspect import isclass
from pathlib import Path
from pkgutil import iter_modules
from typing import TYPE_CHECKING

from discord.ext import commands

from .about_cog import AboutCog
from .admin_cog import AdminCog
from .army_cog import ArmyCog
from .block_cog import BlockCog
from .deck_cog import DeckCog
from .draw_cog import DrawCog
from .events_cog import EventsCog
from .leaderboard_cog import LeaderboardCog
from .league_config_cog import LeagueConfigCog
from .league_profile_cog import LeagueProfileCog
from .league_reminder_cog import LeagueReminderCog
from .leave_cog import LeaveGameCog
from .lfg_cog import LookingForGameCog
from .log_cog import LogCog
from .match_cog import MatchCog
from .owner_cog import OwnerCog
from .score_cog import ScoreCog
from .season_cog import SeasonCog
from .tasks_cog import TasksCog
from .verify_cog import VerifyCog
from .watch_cog import WatchCog
from .mdeck_cog import MDeckCog
from .mdraw_cog import MDrawCog
from .mleaderboard_cog import MLeaderboardCog
from .mlog_cog import MLogCog
from .mprofile_cog import MProfileCog
from .mseason_cog import MSeasonCog
from .wargame_reminder_cog import WargameReminderCog
from .wdraw_cog import WDrawCog
from .wgameconfig_cog import WGameConfigCog
from .wleaderboard_cog import WLeaderboardCog
from .wlog_cog import WLogCog
from .wmatch_cog import WMatchCog
from .wprofile_cog import WProfileCog
from .wseason_cog import WSeasonCog
from .shop_cog import ShopCog
from .shop_admin_cog import ShopAdminCog

if TYPE_CHECKING:
    from discord.ext.commands import AutoShardedBot

logger = logging.getLogger(__name__)

# Only exported cogs will be loaded into the bot at runtime.
__all__ = [
    "AboutCog",
    "AdminCog",
    "ArmyCog",
    "BlockCog",
    "DeckCog",
    "DrawCog",
    "EventsCog",
    "LeaderboardCog",
    "LeagueConfigCog",
    "LeagueProfileCog",
    "LeagueReminderCog",
    "LeaveGameCog",
    "LogCog",
    "MDeckCog",
    "MDrawCog",
    "MLeaderboardCog",
    "MLogCog",
    "MProfileCog",
    "MSeasonCog",
    "LookingForGameCog",
    "MatchCog",
    "OwnerCog",
    "ScoreCog",
    "SeasonCog",
    "ShopAdminCog",
    "ShopCog",
    "TasksCog",
    "VerifyCog",
    "WatchCog",
    "WargameReminderCog",
    "WDrawCog",
    "WGameConfigCog",
    "WLeaderboardCog",
    "WLogCog",
    "WMatchCog",
    "WProfileCog",
    "WSeasonCog",
]


async def load_all_cogs(bot: AutoShardedBot) -> AutoShardedBot:  # pragma: no cover
    # iterate through the modules in the current package
    package_dir = Path(__file__).resolve().parent
    for info in iter_modules([str(package_dir)]):
        # import the module and iterate through its attributes
        module = import_module(f"{__name__}.{info.name}")
        for attribute_name in dir(module):
            attribute = getattr(module, attribute_name)

            # Only load cogs in this module if they're exported
            if (
                isclass(attribute)
                and issubclass(attribute, commands.Cog)
                and attribute.__name__ in __all__
            ):
                if module.__name__ in bot.extensions:
                    logger.info("reloading extension %s...", module.__name__)
                    await bot.reload_extension(module.__name__)
                else:
                    logger.info("loading extension %s...", module.__name__)
                    await bot.load_extension(module.__name__)
                break
    return bot
