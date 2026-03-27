from __future__ import annotations

from asgiref.sync import sync_to_async
from sqlalchemy.dialects.postgresql import insert

from seer.database import DatabaseSession
from seer.models import LeagueGuildConfig


class LeagueConfigService:
    """Manages per-guild league configuration."""

    @sync_to_async()
    def upsert(self, guild_xid: int) -> LeagueGuildConfig:
        """Fetch config for a guild, creating defaults if it doesn't exist."""
        config = (
            DatabaseSession.query(LeagueGuildConfig)
            .filter(LeagueGuildConfig.guild_xid == guild_xid)
            .one_or_none()
        )
        if config is None:
            config = LeagueGuildConfig(guild_xid=guild_xid)
            DatabaseSession.add(config)
            DatabaseSession.commit()
        return config

    @sync_to_async()
    def update(self, guild_xid: int, **fields: object) -> LeagueGuildConfig:
        """Update specific fields on the guild config, creating it if needed."""
        config = (
            DatabaseSession.query(LeagueGuildConfig)
            .filter(LeagueGuildConfig.guild_xid == guild_xid)
            .one_or_none()
        )
        if config is None:
            config = LeagueGuildConfig(guild_xid=guild_xid)
            DatabaseSession.add(config)
        for key, value in fields.items():
            setattr(config, key, value)
        DatabaseSession.commit()
        return config
