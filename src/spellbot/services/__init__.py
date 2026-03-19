from __future__ import annotations

from .apps import AppsService
from .awards import AwardsService, NewAward
from .channels import ChannelsService
from .games import GamesService
from .guilds import GuildsService
from .notifications import NotificationData, NotificationsService
from .patreon import PatreonService
from .plays import PlaysService
from .users import UsersService
from .verifies import VerifiesService
from .watches import WatchesService
from .league_config import LeagueConfigService
from .league_seasons import LeagueSeasonsService
from .league_decks import LeagueDecksService
from .league_matches import LeagueMatchesService
from .league_elo import LeagueEloService
from .wargame_config import WargameConfigService
from .wargame_seasons import WargameSeasonsService
from .wargame_armies import WargameArmiesService
from .wargame_matches import WargameMatchesService
from .wargame_custom_systems import WargameCustomSystemsService
from .wargame_elo import WargameEloService
from .shop import ShopService


class ServicesRegistry:
    def __init__(self) -> None:
        self.apps = AppsService()
        self.awards = AwardsService()
        self.channels = ChannelsService()
        self.games = GamesService()
        self.guilds = GuildsService()
        self.notifications = NotificationsService()
        self.patreon = PatreonService()
        self.plays = PlaysService()
        self.users = UsersService()
        self.verifies = VerifiesService()
        self.watches = WatchesService()
        self.league_config = LeagueConfigService()
        self.league_seasons = LeagueSeasonsService()
        self.league_decks = LeagueDecksService()
        self.league_matches = LeagueMatchesService()
        self.league_elo = LeagueEloService()
        self.wargame_config = WargameConfigService()
        self.wargame_seasons = WargameSeasonsService()
        self.wargame_armies = WargameArmiesService()
        self.wargame_matches = WargameMatchesService()
        self.wargame_custom_systems = WargameCustomSystemsService()
        self.wargame_elo = WargameEloService()
        self.shop = ShopService()


__all__ = [
    "AppsService",
    "AwardsService",
    "ChannelsService",
    "GamesService",
    "GuildsService",
    "LeagueConfigService",
    "LeagueDecksService",
    "LeagueEloService",
    "LeagueMatchesService",
    "LeagueSeasonsService",
    "NewAward",
    "NotificationData",
    "NotificationsService",
    "PatreonService",
    "PlaysService",
    "ServicesRegistry",
    "ShopService",
    "UsersService",
    "VerifiesService",
    "WargameArmiesService",
    "WargameConfigService",
    "WargameCustomSystemsService",
    "WargameEloService",
    "WargameMatchesService",
    "WargameSeasonsService",
    "WatchesService",
]
