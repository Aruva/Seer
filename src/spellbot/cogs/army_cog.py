from __future__ import annotations

import logging
from urllib.parse import urlparse
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from spellbot.database import db_session_manager
from spellbot.settings import settings
from spellbot.utils import for_all_callbacks, is_guild

from ._wargame_helpers import display_game, game_system_autocomplete

if TYPE_CHECKING:
    from spellbot import SpellBot

logger = logging.getLogger(__name__)

# Accepted army list hosting domains (similar to deck list hosts)
VALID_ARMY_LIST_HOSTS = {
    "www.newrecruit.eu",
    "newrecruit.eu",
    "lists.war-game.org",
    "war-game.org",
    "battlescribe.net",
    "rostermaker.com",
    "thetopofthekeep.com",
    "topofthekeep.com",
}


def _validate_army_list(url: str) -> bool:
    try:
        hostname = urlparse(url).hostname or ""
        hostname = hostname.lower().removeprefix("www.")
        return hostname in {h.removeprefix("www.") for h in VALID_ARMY_LIST_HOSTS}
    except Exception:
        return False


@for_all_callbacks(app_commands.check(is_guild))
class ArmyCog(commands.Cog):
    def __init__(self, bot: SpellBot) -> None:
        self.bot = bot

    army_group = app_commands.Group(name="army", description="Manage your wargame armies.")

    # ── /army create ──────────────────────────────────────────────────────────

    @army_group.command(name="create", description="Register a new army.")
    @app_commands.describe(
        game_system="The game system this army belongs to.",
        name="Name for your army (max 64 characters).",
        faction="Optional faction or subfaction name.",
        list_url="Optional URL to your army list.",
    )
    @app_commands.autocomplete(game_system=game_system_autocomplete)
    async def create(
        self,
        interaction: discord.Interaction,
        game_system: str,
        name: str,
        faction: str | None = None,
        list_url: str | None = None,
    ) -> None:
        async with db_session_manager():
            await self._handle_create(interaction, game_system, name, faction, list_url)

    # ── /army list ────────────────────────────────────────────────────────────

    @army_group.command(name="list", description="Show all your registered armies.")
    @app_commands.describe(game_system="Filter by game system.")
    @app_commands.autocomplete(game_system=game_system_autocomplete)
    async def list_armies(
        self, interaction: discord.Interaction, game_system: str
    ) -> None:
        async with db_session_manager():
            await self._handle_list(interaction, game_system)

    # ── /army use ─────────────────────────────────────────────────────────────

    @army_group.command(name="use", description="Set an army as your active army for a game system.")
    @app_commands.describe(
        game_system="The game system.",
        name="Name of the army to activate.",
    )
    @app_commands.autocomplete(game_system=game_system_autocomplete)
    async def use(
        self, interaction: discord.Interaction, game_system: str, name: str
    ) -> None:
        async with db_session_manager():
            await self._handle_use(interaction, game_system, name)

    # ── /army delete ──────────────────────────────────────────────────────────

    @army_group.command(name="delete", description="Delete one of your armies.")
    @app_commands.describe(
        game_system="The game system.",
        name="Name of the army to delete.",
    )
    @app_commands.autocomplete(game_system=game_system_autocomplete)
    async def delete(
        self, interaction: discord.Interaction, game_system: str, name: str
    ) -> None:
        async with db_session_manager():
            await self._handle_delete(interaction, game_system, name)

    # ── /army rename ──────────────────────────────────────────────────────────

    @army_group.command(name="rename", description="Rename one of your armies.")
    @app_commands.describe(
        game_system="The game system.",
        name="Current army name.",
        new_name="New army name.",
    )
    @app_commands.autocomplete(game_system=game_system_autocomplete)
    async def rename(
        self,
        interaction: discord.Interaction,
        game_system: str,
        name: str,
        new_name: str,
    ) -> None:
        async with db_session_manager():
            await self._handle_rename(interaction, game_system, name, new_name)

    # ── /army set-faction ─────────────────────────────────────────────────────

    @army_group.command(name="set-faction", description="Update the faction for an army.")
    @app_commands.describe(
        game_system="The game system.",
        name="Army name.",
        faction="New faction name (leave blank to clear).",
    )
    @app_commands.autocomplete(game_system=game_system_autocomplete)
    async def set_faction(
        self,
        interaction: discord.Interaction,
        game_system: str,
        name: str,
        faction: str | None = None,
    ) -> None:
        async with db_session_manager():
            await self._handle_set_faction(interaction, game_system, name, faction)

    # ── /army set-list ────────────────────────────────────────────────────────

    @army_group.command(name="set-list", description="Update the army list URL for an army.")
    @app_commands.describe(
        game_system="The game system.",
        name="Army name.",
        list_url="New army list URL.",
    )
    @app_commands.autocomplete(game_system=game_system_autocomplete)
    async def set_list(
        self,
        interaction: discord.Interaction,
        game_system: str,
        name: str,
        list_url: str,
    ) -> None:
        async with db_session_manager():
            await self._handle_set_list(interaction, game_system, name, list_url)

    # ── /army stats ───────────────────────────────────────────────────────────

    @army_group.command(name="stats", description="View win/loss stats for an army.")
    @app_commands.describe(
        game_system="The game system.",
        name="Army name (leave blank for your active army).",
    )
    @app_commands.autocomplete(game_system=game_system_autocomplete)
    async def stats(
        self,
        interaction: discord.Interaction,
        game_system: str,
        name: str | None = None,
    ) -> None:
        async with db_session_manager():
            await self._handle_stats(interaction, game_system, name)

    # ── implementations ───────────────────────────────────────────────────────

    async def _handle_create(
        self,
        interaction: discord.Interaction,
        game_system: str,
        name: str,
        faction: str | None,
        list_url: str | None,
    ) -> None:
        assert interaction.guild is not None
        from spellbot.services import WargameArmiesService, WargameConfigService

        if len(name) > 64:
            await interaction.response.send_message(
                "Army name must be 64 characters or fewer.", ephemeral=True
            )
            return

        if faction and len(faction) > 64:
            await interaction.response.send_message(
                "Faction name must be 64 characters or fewer.", ephemeral=True
            )
            return

        if list_url and not _validate_army_list(list_url):
            valid = ", ".join(f"`{h}`" for h in sorted(VALID_ARMY_LIST_HOSTS))
            await interaction.response.send_message(
                f"The army list URL must be from one of: {valid}.", ephemeral=True
            )
            return

        cfg_svc = WargameConfigService()
        config = await cfg_svc.upsert(interaction.guild.id)
        armies_svc = WargameArmiesService()
        count = await armies_svc.count(interaction.guild.id, interaction.user.id, game_system)

        if count >= config.army_limit:
            await interaction.response.send_message(
                f"You have reached the army limit of {config.army_limit} "
                f"for {display_game(game_system)}.",
                ephemeral=True,
            )
            return

        existing = await armies_svc.get_by_name(
            interaction.guild.id, interaction.user.id, game_system, name
        )
        if existing:
            await interaction.response.send_message(
                f'You already have a {display_game(game_system)} army named "{name}".',
                ephemeral=True,
            )
            return

        await armies_svc.create(
            interaction.guild.id,
            interaction.user.id,
            game_system,
            name,
            faction=faction,
            list_url=list_url,
            set_as_current=True,
        )
        await interaction.response.send_message(
            f'✅ Army **{name}** created and set as your active {display_game(game_system)} army.',
            ephemeral=True,
        )

    async def _handle_list(
        self, interaction: discord.Interaction, game_system: str
    ) -> None:
        assert interaction.guild is not None
        from spellbot.services import WargameArmiesService

        armies_svc = WargameArmiesService()
        armies = await armies_svc.list_all(interaction.guild.id, interaction.user.id, game_system)

        if not armies:
            await interaction.response.send_message(
                f"You have no registered {display_game(game_system)} armies. "
                "Use `/army create` to add one.",
                ephemeral=True,
            )
            return

        profile = await armies_svc.get_profile(
            interaction.guild.id, interaction.user.id, game_system
        )
        current_id = profile.current_army_id

        lines = []
        for army in armies:
            marker = "▶ " if army.id == current_id else "  "
            label = army.name
            if army.faction:
                label += f" ({army.faction})"
            if army.list_url:
                lines.append(f"{marker}[{label}]({army.list_url})")
            else:
                lines.append(f"{marker}{label}")

        embed = discord.Embed(
            title=f"Your {display_game(game_system)} Armies",
            description="\n".join(lines),
            color=discord.Color.blue(),
        )
        embed.set_footer(text="▶ = currently active army")
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _handle_use(
        self, interaction: discord.Interaction, game_system: str, name: str
    ) -> None:
        assert interaction.guild is not None
        from spellbot.services import WargameArmiesService

        armies_svc = WargameArmiesService()
        army = await armies_svc.get_by_name(
            interaction.guild.id, interaction.user.id, game_system, name
        )
        if army is None:
            await interaction.response.send_message(
                f'You have no {display_game(game_system)} army named "{name}".', ephemeral=True
            )
            return

        await armies_svc.set_current(interaction.guild.id, interaction.user.id, game_system, army)
        await interaction.response.send_message(
            f'✅ **{name}** is now your active {display_game(game_system)} army.', ephemeral=True
        )

    async def _handle_delete(
        self, interaction: discord.Interaction, game_system: str, name: str
    ) -> None:
        assert interaction.guild is not None
        from spellbot.services import WargameArmiesService

        armies_svc = WargameArmiesService()
        army = await armies_svc.get_by_name(
            interaction.guild.id, interaction.user.id, game_system, name
        )
        if army is None:
            await interaction.response.send_message(
                f'You have no {display_game(game_system)} army named "{name}".', ephemeral=True
            )
            return

        await armies_svc.delete(interaction.guild.id, interaction.user.id, army)
        await interaction.response.send_message(
            f'🗑️ Army **{name}** has been deleted.', ephemeral=True
        )

    async def _handle_rename(
        self,
        interaction: discord.Interaction,
        game_system: str,
        name: str,
        new_name: str,
    ) -> None:
        assert interaction.guild is not None
        from spellbot.services import WargameArmiesService

        if len(new_name) > 64:
            await interaction.response.send_message(
                "New name must be 64 characters or fewer.", ephemeral=True
            )
            return

        armies_svc = WargameArmiesService()
        army = await armies_svc.get_by_name(
            interaction.guild.id, interaction.user.id, game_system, name
        )
        if army is None:
            await interaction.response.send_message(
                f'You have no {display_game(game_system)} army named "{name}".', ephemeral=True
            )
            return

        conflict = await armies_svc.get_by_name(
            interaction.guild.id, interaction.user.id, game_system, new_name
        )
        if conflict:
            await interaction.response.send_message(
                f'You already have a {display_game(game_system)} army named "{new_name}".',
                ephemeral=True,
            )
            return

        await armies_svc.rename(army, new_name)
        await interaction.response.send_message(
            f'✅ Army renamed from **{name}** to **{new_name}**.', ephemeral=True
        )

    async def _handle_set_faction(
        self,
        interaction: discord.Interaction,
        game_system: str,
        name: str,
        faction: str | None,
    ) -> None:
        assert interaction.guild is not None
        from spellbot.services import WargameArmiesService

        if faction and len(faction) > 64:
            await interaction.response.send_message(
                "Faction name must be 64 characters or fewer.", ephemeral=True
            )
            return

        armies_svc = WargameArmiesService()
        army = await armies_svc.get_by_name(
            interaction.guild.id, interaction.user.id, game_system, name
        )
        if army is None:
            await interaction.response.send_message(
                f'You have no {display_game(game_system)} army named "{name}".', ephemeral=True
            )
            return

        await armies_svc.set_faction(army, faction)
        if faction:
            await interaction.response.send_message(
                f'✅ Faction for **{name}** updated to **{faction}**.', ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f'✅ Faction for **{name}** has been cleared.', ephemeral=True
            )

    async def _handle_set_list(
        self,
        interaction: discord.Interaction,
        game_system: str,
        name: str,
        list_url: str,
    ) -> None:
        assert interaction.guild is not None
        from spellbot.services import WargameArmiesService

        if not _validate_army_list(list_url):
            valid = ", ".join(f"`{h}`" for h in sorted(VALID_ARMY_LIST_HOSTS))
            await interaction.response.send_message(
                f"The army list URL must be from one of: {valid}.", ephemeral=True
            )
            return

        armies_svc = WargameArmiesService()
        army = await armies_svc.get_by_name(
            interaction.guild.id, interaction.user.id, game_system, name
        )
        if army is None:
            await interaction.response.send_message(
                f'You have no {display_game(game_system)} army named "{name}".', ephemeral=True
            )
            return

        await armies_svc.set_list_url(army, list_url)
        await interaction.response.send_message(
            f'✅ Army list updated for **{name}**.', ephemeral=True
        )

    async def _handle_stats(
        self,
        interaction: discord.Interaction,
        game_system: str,
        name: str | None,
    ) -> None:
        assert interaction.guild is not None
        from spellbot.services import WargameArmiesService, WargameSeasonsService

        armies_svc = WargameArmiesService()

        if name is None:
            profile = await armies_svc.get_profile(
                interaction.guild.id, interaction.user.id, game_system
            )
            if not profile.current_army_id:
                await interaction.response.send_message(
                    f"You have no active {display_game(game_system)} army. "
                    "Use `/army use` to select one.",
                    ephemeral=True,
                )
                return
            army = await armies_svc.get_by_id(profile.current_army_id)
        else:
            army = await armies_svc.get_by_name(
                interaction.guild.id, interaction.user.id, game_system, name
            )

        if army is None:
            await interaction.response.send_message(
                f'No {display_game(game_system)} army named "{name}" found.'
                if name
                else "Army not found.",
                ephemeral=True,
            )
            return

        all_stats = await armies_svc.get_army_stats(
            interaction.guild.id, interaction.user.id, army.id
        )

        label = army.name
        if army.faction:
            label += f" ({army.faction})"
        display_label = f"[{label}]({army.list_url})" if army.list_url else label

        embed = discord.Embed(
            title=f"Army Stats — {army.name}",
            description=f"Overall statistics for {display_label}.",
            color=discord.Color.blue(),
        )
        if army.list_url:
            embed.url = army.list_url
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        total = all_stats["total"]
        wins = all_stats["wins"]
        draws = all_stats["draws"]
        losses = all_stats["losses"]
        win_rate = round(wins / total * 100) if total else 0

        embed.add_field(name="Matches", value=f"{total} game{'s' if total != 1 else ''}")
        embed.add_field(name="Wins", value=str(wins))
        embed.add_field(name="Draws", value=str(draws))
        embed.add_field(name="Losses", value=str(losses))
        embed.add_field(name="Win Rate", value=f"{win_rate}%")

        seasons_svc = WargameSeasonsService()
        active = await seasons_svc.get_active(interaction.guild.id, game_system)
        if active:
            from spellbot.services import WargameMatchesService
            matches_svc = WargameMatchesService()
            season_matches = await matches_svc.get_for_user(
                interaction.guild.id,
                interaction.user.id,
                season_id=active.id,
                army_id=army.id,
            )
            sw = sum(1 for m in season_matches if m.winner_xid == interaction.user.id)
            sd = sum(1 for m in season_matches if m.winner_xid is None)
            sl = len(season_matches) - sw - sd
            sr = round(sw / len(season_matches) * 100) if season_matches else 0
            embed.add_field(
                name=f"This Season ({active.name})",
                value=f"{len(season_matches)} games · {sw}W {sd}D {sl}L · {sr}% win rate",
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: SpellBot) -> None:  # pragma: no cover
    await bot.add_cog(ArmyCog(bot), guild=settings.GUILD_OBJECT)
