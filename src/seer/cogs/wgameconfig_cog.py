from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from seer.database import db_session_manager
from seer.models import KNOWN_GAME_SYSTEMS, WARGAME_CONFIG_GLOBAL
from seer.settings import settings
from seer.utils import for_all_callbacks, is_guild

from ._wargame_helpers import display_game, game_system_autocomplete

if TYPE_CHECKING:
    from seer import Seer

logger = logging.getLogger(__name__)

# Max custom game systems per guild
MAX_CUSTOM_SYSTEMS = 20
# Slug validation: lowercase letters, digits, hyphens
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{0,62}$")


@for_all_callbacks(app_commands.check(is_guild))
class WGameConfigCog(commands.Cog):
    def __init__(self, bot: Seer) -> None:
        self.bot = bot

    wgc_group = app_commands.Group(
        name="wgameconfig",
        description="Configure wargame league settings for this server.",
        default_permissions=discord.Permissions(manage_guild=True),
    )

    # ── Game system management ────────────────────────────────────────────────

    @wgc_group.command(
        name="add-game",
        description="Register a custom game system beyond the built-in ones.",
    )
    @app_commands.describe(
        slug="Short URL-safe identifier (e.g. 'bolt-action', 'age-of-sigmar').",
        display_name="Human-readable name shown in embeds (e.g. 'Bolt Action').",
    )
    async def add_game(
        self,
        interaction: discord.Interaction,
        slug: str,
        display_name: str,
    ) -> None:
        async with db_session_manager():
            await self._handle_add_game(interaction, slug, display_name)

    @wgc_group.command(name="remove-game", description="Remove a custom game system.")
    @app_commands.describe(slug="Slug of the custom game system to remove.")
    @app_commands.autocomplete(slug=game_system_autocomplete)
    async def remove_game(
        self,
        interaction: discord.Interaction,
        slug: str,
    ) -> None:
        async with db_session_manager():
            await self._handle_remove_game(interaction, slug)

    @wgc_group.command(name="list-games", description="List all game systems available on this server.")
    async def list_games(self, interaction: discord.Interaction) -> None:
        async with db_session_manager():
            await self._handle_list_games(interaction)

    # ── Per-system or global numeric settings ─────────────────────────────────

    @wgc_group.command(
        name="minimum-games",
        description="Minimum confirmed games required to appear on the wargame leaderboard.",
    )
    @app_commands.describe(
        amount="Number of games required (leave blank to view current).",
        game_system="Game system to configure (leave blank for global default).",
    )
    @app_commands.autocomplete(game_system=game_system_autocomplete)
    async def minimum_games(
        self,
        interaction: discord.Interaction,
        amount: int | None = None,
        game_system: str = WARGAME_CONFIG_GLOBAL,
    ) -> None:
        async with db_session_manager():
            await self._update(interaction, "minimum_games", amount, "Minimum games", game_system)

    @wgc_group.command(name="points-gained", description="Points awarded per wargame match win.")
    @app_commands.describe(
        amount="Points per win (leave blank to view current).",
        game_system="Game system to configure (leave blank for global default).",
    )
    @app_commands.autocomplete(game_system=game_system_autocomplete)
    async def points_gained(
        self,
        interaction: discord.Interaction,
        amount: int | None = None,
        game_system: str = WARGAME_CONFIG_GLOBAL,
    ) -> None:
        async with db_session_manager():
            await self._update(interaction, "points_gained", amount, "Points per win", game_system)

    @wgc_group.command(name="points-lost", description="Points deducted per wargame match loss.")
    @app_commands.describe(
        amount="Points per loss (leave blank to view current).",
        game_system="Game system to configure (leave blank for global default).",
    )
    @app_commands.autocomplete(game_system=game_system_autocomplete)
    async def points_lost(
        self,
        interaction: discord.Interaction,
        amount: int | None = None,
        game_system: str = WARGAME_CONFIG_GLOBAL,
    ) -> None:
        async with db_session_manager():
            await self._update(interaction, "points_lost", amount, "Points per loss", game_system)

    @wgc_group.command(name="points-per-draw", description="Points awarded per wargame draw.")
    @app_commands.describe(
        amount="Points per draw (leave blank to view current).",
        game_system="Game system to configure (leave blank for global default).",
    )
    @app_commands.autocomplete(game_system=game_system_autocomplete)
    async def points_per_draw(
        self,
        interaction: discord.Interaction,
        amount: int | None = None,
        game_system: str = WARGAME_CONFIG_GLOBAL,
    ) -> None:
        async with db_session_manager():
            await self._update(
                interaction, "points_per_draw", amount, "Points per draw", game_system
            )

    @wgc_group.command(
        name="base-points",
        description="Offset added to all displayed wargame point totals.",
    )
    @app_commands.describe(
        amount="Base point offset (leave blank to view current).",
        game_system="Game system to configure (leave blank for global default).",
    )
    @app_commands.autocomplete(game_system=game_system_autocomplete)
    async def base_points(
        self,
        interaction: discord.Interaction,
        amount: int | None = None,
        game_system: str = WARGAME_CONFIG_GLOBAL,
    ) -> None:
        async with db_session_manager():
            await self._update(interaction, "base_points", amount, "Base points", game_system)

    @wgc_group.command(
        name="army-limit",
        description="Maximum armies a player can register per game system.",
    )
    @app_commands.describe(
        amount="Army limit (leave blank to view current).",
        game_system="Game system to configure (leave blank for global default).",
    )
    @app_commands.autocomplete(game_system=game_system_autocomplete)
    async def army_limit(
        self,
        interaction: discord.Interaction,
        amount: int | None = None,
        game_system: str = WARGAME_CONFIG_GLOBAL,
    ) -> None:
        async with db_session_manager():
            await self._update(interaction, "army_limit", amount, "Army limit", game_system)

    @wgc_group.command(
        name="reminder-hours",
        description="Hours after which unconfirmed players receive a reminder DM.",
    )
    @app_commands.describe(
        amount="Hours before reminder (0 = disable reminders; leave blank to view current).",
        game_system="Game system to configure (leave blank for global default).",
    )
    @app_commands.autocomplete(game_system=game_system_autocomplete)
    async def reminder_hours(
        self,
        interaction: discord.Interaction,
        amount: int | None = None,
        game_system: str = WARGAME_CONFIG_GLOBAL,
    ) -> None:
        async with db_session_manager():
            await self._update(
                interaction, "reminder_hours", amount, "Reminder hours", game_system
            )

    # ── Boolean settings ──────────────────────────────────────────────────────

    @wgc_group.command(name="enable-draws", description="Allow or disallow wargame draw logging.")
    @app_commands.describe(
        enabled="True to allow draws, False to disable (leave blank to view).",
        game_system="Game system to configure (leave blank for global default).",
    )
    @app_commands.autocomplete(game_system=game_system_autocomplete)
    async def enable_draws(
        self,
        interaction: discord.Interaction,
        enabled: bool | None = None,
        game_system: str = WARGAME_CONFIG_GLOBAL,
    ) -> None:
        async with db_session_manager():
            assert interaction.guild is not None
            from seer.services import WargameConfigService

            svc = WargameConfigService()
            scope = display_game(game_system) if game_system != WARGAME_CONFIG_GLOBAL else "global"
            if enabled is not None:
                config = await svc.update(interaction.guild.id, game_system, enable_draws=enabled)
            else:
                config = await svc.upsert(interaction.guild.id, game_system)

            status = "enabled" if config.enable_draws else "disabled"
            verb = "is now" if enabled is not None else "is currently"
            await interaction.response.send_message(
                f"[{scope}] Wargame draws {verb} **{status}**.", ephemeral=True
            )

    @wgc_group.command(
        name="dispute-role",
        description="Set or clear the role added to wargame dispute threads.",
    )
    @app_commands.describe(
        role="Role to add to dispute threads.",
        unset="Set to True to remove the dispute role.",
        game_system="Game system to configure (leave blank for global default).",
    )
    @app_commands.autocomplete(game_system=game_system_autocomplete)
    async def dispute_role(
        self,
        interaction: discord.Interaction,
        role: discord.Role | None = None,
        unset: bool = False,
        game_system: str = WARGAME_CONFIG_GLOBAL,
    ) -> None:
        async with db_session_manager():
            assert interaction.guild is not None
            from seer.services import WargameConfigService

            svc = WargameConfigService()
            scope = display_game(game_system) if game_system != WARGAME_CONFIG_GLOBAL else "global"
            if unset:
                await svc.update(interaction.guild.id, game_system, dispute_role_xid=None)
                await interaction.response.send_message(
                    f"[{scope}] Wargame dispute role has been cleared.", ephemeral=True
                )
            elif role is not None:
                await svc.update(interaction.guild.id, game_system, dispute_role_xid=role.id)
                await interaction.response.send_message(
                    f"[{scope}] Wargame dispute role is now {role.mention}.", ephemeral=True
                )
            else:
                config = await svc.upsert(interaction.guild.id, game_system)
                if config.dispute_role_xid:
                    await interaction.response.send_message(
                        f"[{scope}] Wargame dispute role is currently "
                        f"<@&{config.dispute_role_xid}>.",
                        ephemeral=True,
                    )
                else:
                    await interaction.response.send_message(
                        f"[{scope}] No wargame dispute role is currently set.", ephemeral=True
                    )

    # ── Implementations ───────────────────────────────────────────────────────

    async def _handle_add_game(
        self,
        interaction: discord.Interaction,
        slug: str,
        display_name: str,
    ) -> None:
        assert interaction.guild is not None
        from seer.services import WargameCustomSystemsService

        slug = slug.lower().strip()

        # Validate slug format
        if not SLUG_RE.match(slug):
            await interaction.response.send_message(
                "Slug must be lowercase letters, digits, and hyphens only "
                "(e.g. `bolt-action`, `age-of-sigmar`).",
                ephemeral=True,
            )
            return

        # Don't shadow built-in systems
        if slug in KNOWN_GAME_SYSTEMS:
            await interaction.response.send_message(
                f'`{slug}` is already a built-in game system — no need to add it.',
                ephemeral=True,
            )
            return

        if len(display_name) > 128:
            await interaction.response.send_message(
                "Display name must be 128 characters or fewer.", ephemeral=True
            )
            return

        svc = WargameCustomSystemsService()

        # Check limit
        count = await svc.count(interaction.guild.id)
        if count >= MAX_CUSTOM_SYSTEMS:
            await interaction.response.send_message(
                f"This server has reached the custom game system limit of {MAX_CUSTOM_SYSTEMS}.",
                ephemeral=True,
            )
            return

        # Check for duplicate slug
        existing = await svc.get_by_slug(interaction.guild.id, slug)
        if existing is not None:
            await interaction.response.send_message(
                f'A custom game system with slug `{slug}` already exists: '
                f'**{existing.display_name}**.',
                ephemeral=True,
            )
            return

        await svc.create(interaction.guild.id, slug, display_name)
        await interaction.response.send_message(
            f'✅ Custom game system **{display_name}** (`{slug}`) has been registered. '
            "Players can now use it in `/wlog`, `/army`, `/wseason`, etc.",
            ephemeral=True,
        )

    async def _handle_remove_game(
        self,
        interaction: discord.Interaction,
        slug: str,
    ) -> None:
        assert interaction.guild is not None
        from seer.services import WargameCustomSystemsService

        # Don't allow removing built-ins
        if slug in KNOWN_GAME_SYSTEMS:
            await interaction.response.send_message(
                f'`{slug}` is a built-in game system and cannot be removed.',
                ephemeral=True,
            )
            return

        svc = WargameCustomSystemsService()
        system = await svc.get_by_slug(interaction.guild.id, slug)
        if system is None:
            await interaction.response.send_message(
                f'No custom game system with slug `{slug}` found.', ephemeral=True
            )
            return

        name = system.display_name
        await svc.delete(system)
        await interaction.response.send_message(
            f'🗑️ Custom game system **{name}** (`{slug}`) has been removed.\n'
            "⚠️ Existing seasons and match history are preserved but the system "
            "will no longer appear in autocomplete.",
            ephemeral=True,
        )

    async def _handle_list_games(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None
        from seer.services import WargameCustomSystemsService

        svc = WargameCustomSystemsService()
        custom = await svc.list_for_guild(interaction.guild.id)

        embed = discord.Embed(
            title="Game Systems on this Server",
            color=discord.Color.blue(),
        )

        built_in_lines = [f"`{slug}` — {label}" for slug, label in KNOWN_GAME_SYSTEMS.items()]
        embed.add_field(
            name="Built-in",
            value="\n".join(built_in_lines),
            inline=False,
        )

        if custom:
            custom_lines = [f"`{c.slug}` — {c.display_name}" for c in custom]
            embed.add_field(
                name="Custom (this server)",
                value="\n".join(custom_lines),
                inline=False,
            )
        else:
            embed.add_field(
                name="Custom (this server)",
                value="None — use `/wgameconfig add-game` to add one.",
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _update(
        self,
        interaction: discord.Interaction,
        field: str,
        value: int | None,
        label: str,
        game_system: str,
    ) -> None:
        assert interaction.guild is not None
        from seer.services import WargameConfigService

        scope = display_game(game_system) if game_system != WARGAME_CONFIG_GLOBAL else "global"
        svc = WargameConfigService()
        if value is not None:
            if value < 0:
                await interaction.response.send_message(
                    "Value must be 0 or greater.", ephemeral=True
                )
                return
            config = await svc.update(interaction.guild.id, game_system, **{field: value})
        else:
            config = await svc.upsert(interaction.guild.id, game_system)

        current = getattr(config, field)
        verb = "is now" if value is not None else "is currently"
        await interaction.response.send_message(
            f"[{scope}] {label} {verb} **{current}**.", ephemeral=True
        )


async def setup(bot: Seer) -> None:  # pragma: no cover
    await bot.add_cog(WGameConfigCog(bot), guild=settings.GUILD_OBJECT)
