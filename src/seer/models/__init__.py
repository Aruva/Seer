from __future__ import annotations

from importlib import import_module
from inspect import getmembers, isclass
from pathlib import Path
from pkgutil import iter_modules


def import_models() -> None:  # pragma: no cover
    package_dir = Path(__file__).resolve().parent
    for info in iter_modules([str(package_dir)]):
        module = import_module(f"{__name__}.{info.name}")
        for name, _object in getmembers(module, isclass):
            if isclass(_object) and issubclass(_object, Base) and name not in globals():
                globals()[name] = _object


from .base import Base, create_all, literalquery, now, reverse_all  # noqa: I001,E402

from .award import GuildAward, UserAward, GuildAwardDict, UserAwardDict  # noqa: E402
from .block import Block, BlockDict  # noqa: E402
from .channel import Channel, ChannelDict  # noqa: E402
from .game import Game, GameStatus, GameDict, GameLinkDetails, MAX_RULES_LENGTH  # noqa: E402
from .guild import Guild, GuildDict  # noqa: E402
from .notification import Notification, NotificationDict  # noqa: E402
from .play import Play, PlayDict  # noqa: E402
from .post import Post, PostDict  # noqa: E402
from .queue import Queue, QueueDict  # noqa: E402
from .token import Token, TokenDict  # noqa: E402
from .user import User, UserDict  # noqa: E402
from .verify import Verify, VerifyDict  # noqa: E402
from .watch import Watch, WatchDict  # noqa: E402
from .infraction import Infraction, InfractionDict  # noqa: E402
from .league_config import LeagueGuildConfig  # noqa: E402
from .league_season import LeagueSeason  # noqa: E402
from .league_deck import LeagueDeck, VALID_DECK_LIST_HOSTS  # noqa: E402
from .league_profile import LeagueProfile  # noqa: E402
from .league_match import LeagueMatch, LeagueMatchPlayer  # noqa: E402
from .league_elo import LeagueElo  # noqa: E402
from .wargame_config import WargameGuildConfig, WARGAME_CONFIG_GLOBAL  # noqa: E402
from .wargame_season import WargameSeason  # noqa: E402
from .wargame_army import WargameArmy, KNOWN_GAME_SYSTEMS, KNOWN_MAGIC_FORMATS  # noqa: E402
from .wargame_profile import WargameProfile  # noqa: E402
from .wargame_match import WargameMatch, WargameMatchPlayer  # noqa: E402
from .wargame_custom_system import WargameCustomSystem  # noqa: E402
from .wargame_elo import WargameElo  # noqa: E402
from .shop_product import ShopProduct  # noqa: E402
from .shop_order import ShopOrder  # noqa: E402

__all__ = [
    "MAX_RULES_LENGTH",
    "Base",
    "Block",
    "BlockDict",
    "Channel",
    "ChannelDict",
    "Game",
    "GameDict",
    "GameDict",
    "GameLinkDetails",
    "GameStatus",
    "Guild",
    "GuildAward",
    "GuildAwardDict",
    "GuildDict",
    "Notification",
    "NotificationDict",
    "Play",
    "PlayDict",
    "Post",
    "PostDict",
    "Queue",
    "QueueDict",
    "Token",
    "TokenDict",
    "User",
    "UserAward",
    "UserAwardDict",
    "UserDict",
    "Verify",
    "VerifyDict",
    "Watch",
    "WatchDict",
    "Infraction",
    "InfractionDict",
    "LeagueGuildConfig",
    "LeagueSeason",
    "LeagueDeck",
    "VALID_DECK_LIST_HOSTS",
    "LeagueProfile",
    "LeagueElo",
    "LeagueMatch",
    "LeagueMatchPlayer",
    "WARGAME_CONFIG_GLOBAL",
    "WargameCustomSystem",
    "WargameGuildConfig",
    "WargameSeason",
    "WargameArmy",
    "KNOWN_GAME_SYSTEMS",
    "KNOWN_MAGIC_FORMATS",
    "WargameProfile",
    "WargameMatch",
    "WargameMatchPlayer",
    "WargameElo",
    "ShopProduct",
    "ShopOrder",
    "create_all",
    "import_models",
    "literalquery",
    "now",
    "reverse_all",
]
