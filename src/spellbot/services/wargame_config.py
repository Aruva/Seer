from __future__ import annotations

from asgiref.sync import sync_to_async

from spellbot.database import DatabaseSession
from spellbot.models import WARGAME_CONFIG_GLOBAL, WargameGuildConfig


class WargameConfigService:
    """Manages per-guild, per-game-system wargame configuration.

    Rows with game_system='*' are the global default.  When fetching config
    for a specific game system, the service first looks for an exact match;
    if none exists it falls back to the global default row.
    """

    @sync_to_async()
    def upsert(
        self,
        guild_xid: int,
        game_system: str = WARGAME_CONFIG_GLOBAL,
    ) -> WargameGuildConfig:
        """Get or create a config row.  Falls back to global if specific not found."""
        config = (
            DatabaseSession.query(WargameGuildConfig)
            .filter_by(guild_xid=guild_xid, game_system=game_system)
            .one_or_none()
        )
        if config is None and game_system != WARGAME_CONFIG_GLOBAL:
            # Try global default
            config = (
                DatabaseSession.query(WargameGuildConfig)
                .filter_by(guild_xid=guild_xid, game_system=WARGAME_CONFIG_GLOBAL)
                .one_or_none()
            )
        if config is None:
            config = WargameGuildConfig(
                guild_xid=guild_xid, game_system=WARGAME_CONFIG_GLOBAL
            )
            DatabaseSession.add(config)
            DatabaseSession.flush()
        return config

    @sync_to_async()
    def update(
        self,
        guild_xid: int,
        game_system: str = WARGAME_CONFIG_GLOBAL,
        **fields: object,
    ) -> WargameGuildConfig:
        """Update config fields for the given game system (or global default).

        If no specific row exists for the given game_system, one is created
        inheriting defaults — it does NOT copy values from the global row,
        so admins only override what they explicitly set.
        """
        config = (
            DatabaseSession.query(WargameGuildConfig)
            .filter_by(guild_xid=guild_xid, game_system=game_system)
            .one_or_none()
        )
        if config is None:
            config = WargameGuildConfig(guild_xid=guild_xid, game_system=game_system)
            DatabaseSession.add(config)
        for key, value in fields.items():
            setattr(config, key, value)
        DatabaseSession.flush()
        return config

    @sync_to_async()
    def list_for_guild(self, guild_xid: int) -> list[WargameGuildConfig]:
        """Return all config rows for this guild (global + per-system)."""
        return (
            DatabaseSession.query(WargameGuildConfig)
            .filter_by(guild_xid=guild_xid)
            .order_by(WargameGuildConfig.game_system)
            .all()
        )
