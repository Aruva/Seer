from __future__ import annotations

"""Shared helpers for wargame cogs (not a cog itself)."""

import logging
from typing import TYPE_CHECKING

import discord

from seer.models import KNOWN_GAME_SYSTEMS
from seer.services.wargame_elo import WARGAME_ELO_ALERT_THRESHOLD, DEFAULT_ELO

if TYPE_CHECKING:
    from seer import Seer

logger = logging.getLogger(__name__)

# ── Static choice list for built-in game systems ──────────────────────────────

GAME_SYSTEM_CHOICES = [
    discord.app_commands.Choice(name=label, value=slug)
    for slug, label in KNOWN_GAME_SYSTEMS.items()
]

# ── Common shorthand aliases players might type ───────────────────────────────

GAME_SYSTEM_ALIASES: dict[str, str] = {
    # Warmachine / Hordes
    "wm": "warmachine",
    "wm/h": "warmachine",
    "wmh": "warmachine",
    "warmachine/hordes": "warmachine",
    "hordes": "warmachine",
    # Warhammer 40K
    "40k": "warhammer40k",
    "wh40k": "warhammer40k",
    "warhammer": "warhammer40k",
    "40000": "warhammer40k",
}


def normalize_game_system(slug: str) -> str:
    """Resolve common aliases to canonical slugs.

    If the slug is not an alias and not a known system, it is returned
    as-is so custom game systems still work.
    """
    key = slug.lower().strip()
    return GAME_SYSTEM_ALIASES.get(key, key)


def display_game(game_system: str) -> str:
    """Return a human-readable label for a game system slug."""
    return KNOWN_GAME_SYSTEMS.get(game_system, game_system.replace("-", " ").title())


# ── Autocomplete callback (registered on all wargame commands) ────────────────

async def game_system_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[discord.app_commands.Choice[str]]:
    """Combine built-in and guild-defined game systems for autocomplete."""
    assert interaction.guild is not None
    from seer.database import db_session_manager
    from seer.services import WargameCustomSystemsService

    try:
        async with db_session_manager():
            svc = WargameCustomSystemsService()
            custom = await svc.list_for_guild(interaction.guild.id)
    except Exception:
        custom = []

    # Build the combined list: built-ins first, then custom
    all_systems: list[tuple[str, str]] = list(KNOWN_GAME_SYSTEMS.items()) + [
        (c.slug, c.display_name) for c in custom
    ]

    query = normalize_game_system(current) if current else ""
    results: list[discord.app_commands.Choice[str]] = []
    for slug, label in all_systems:
        if not query or query in slug.lower() or query in label.lower():
            results.append(discord.app_commands.Choice(name=label, value=slug))

    return results[:25]


# ── ELO alert DMs ─────────────────────────────────────────────────────────────

async def _send_wargame_elo_alert_dms(
    bot: Seer,
    guild_id: int,
    player_xids: list[int],
    elo_rows: dict,  # {uid: WargameElo}
    game_system: str,
) -> None:
    """DM both players when the ELO spread is ≥ WARGAME_ELO_ALERT_THRESHOLD."""
    game_label = display_game(game_system)
    elos = {uid: elo_rows[uid].elo for uid in player_xids}
    games = {uid: elo_rows[uid].games_played for uid in player_xids}

    sorted_players = sorted(player_xids, key=lambda uid: elos[uid], reverse=True)
    top_uid = sorted_players[0]
    low_uid = sorted_players[1]
    spread = elos[top_uid] - elos[low_uid]

    if spread < WARGAME_ELO_ALERT_THRESHOLD:
        return

    for uid in player_xids:
        opponent_uid = low_uid if uid == top_uid else top_uid

        if uid == top_uid:
            status = "⭐ **You are the higher-rated player** in this match."
        else:
            status = "🐉 **You are the underdog** in this match — an upset win is worth more ELO."

        embed = discord.Embed(
            title=f"⚔️ {game_label} — ELO Matchup Alert",
            description=(
                f"A match has been logged against <@{opponent_uid}>. "
                "Here are the pre-match ratings:"
            ),
            color=discord.Color.orange(),
        )

        standings_lines = []
        for p in sorted_players:
            g = games[p]
            tier = "provisional" if g < 30 else "standard" if g < 60 else "established"
            standings_lines.append(
                f"<@{p}> — **{elos[p]}** ELO *(K-factor: {tier}, {g} games)*"
            )
        embed.add_field(
            name="Current Ratings",
            value="\n".join(standings_lines),
            inline=False,
        )
        embed.add_field(name="Rating Spread", value=f"{spread} points", inline=True)
        embed.add_field(name="Status", value=status, inline=False)
        embed.add_field(
            name="ℹ️ How ELO works",
            value=(
                "Your rating changes based on the expected vs. actual result. "
                "Beating a higher-rated opponent earns more ELO; losing to a lower-rated "
                "opponent costs more. ELO updates once both players confirm the match."
            ),
            inline=False,
        )
        embed.set_footer(text="SouthSeer — Southside Studio and Hobbies")

        try:
            user = await bot.fetch_user(uid)
            await user.send(embed=embed)
        except Exception:
            pass  # DMs disabled; silently skip


# ── Core match-logging helper ─────────────────────────────────────────────────

async def log_wargame_match(
    bot: Seer,
    interaction: discord.Interaction,
    game_system: str,
    opponent: discord.Member,
    is_win: bool,
) -> None:
    """Create and post a 1v1 wargame match confirmation embed."""
    assert interaction.guild is not None

    # Resolve any alias the user may have typed manually
    game_system = normalize_game_system(game_system)

    if opponent.id == interaction.user.id:
        await interaction.response.send_message(
            "You cannot log a match against yourself.", ephemeral=True
        )
        return

    from seer.services import (
        WargameArmiesService,
        WargameConfigService,
        WargameMatchesService,
        WargameSeasonsService,
        WargameEloService,
    )

    seasons_svc = WargameSeasonsService()
    season = await seasons_svc.get_active(interaction.guild.id, game_system)
    if season is None:
        await interaction.response.send_message(
            f"There is no active {display_game(game_system)} season. "
            "An admin must start one with `/wseason start`.",
            ephemeral=True,
        )
        return

    if not is_win:
        cfg_svc = WargameConfigService()
        config = await cfg_svc.upsert(interaction.guild.id, game_system)
        if not config.enable_draws:
            await interaction.response.send_message(
                "Draws are currently disabled on this server.", ephemeral=True
            )
            return

    player_xids = [interaction.user.id, opponent.id]

    # ── ELO lookup ────────────────────────────────────────────────────────────
    elo_svc = WargameEloService()
    elo_rows = await elo_svc.get_for_users(interaction.guild.id, player_xids, game_system)
    elos = {uid: elo_rows[uid].elo for uid in player_xids}

    # ── Army lookup ───────────────────────────────────────────────────────────
    armies_svc = WargameArmiesService()
    army_ids: list[int | None] = []
    army_labels: list[str] = []

    for uid in player_xids:
        profile = await armies_svc.get_profile(interaction.guild.id, uid, game_system)
        if profile.current_army_id:
            army = await armies_svc.get_by_id(profile.current_army_id)
            if army:
                army_ids.append(army.id)
                label = army.name
                if army.faction:
                    label += f" ({army.faction})"
                if army.list_url:
                    label = f"[{label}]({army.list_url})"
                army_labels.append(label)
            else:
                army_ids.append(None)
                army_labels.append("Not specified")
        else:
            army_ids.append(None)
            army_labels.append("Not specified")

    from seer.views import WargameMatchView

    game_label = display_game(game_system)
    color = discord.Color.green() if is_win else discord.Color.blue()
    embed = discord.Embed(
        title=f"{game_label} — Match Confirmation",
        description=(
            "The match will be recorded as a **win** for the player who logged it."
            if is_win
            else "The match will be recorded as a **draw**."
        )
        + "\n\nClick below to confirm or dispute.",
        color=color,
    )
    embed.add_field(
        name="Player",
        value="\n".join(f"<@{uid}>" for uid in player_xids),
        inline=True,
    )
    embed.add_field(name="Army", value="\n".join(army_labels), inline=True)

    # ── ELO ratings field (always shown) ─────────────────────────────────────
    elo_lines = []
    for uid in player_xids:
        elo_val = elos[uid]
        g = elo_rows[uid].games_played
        elo_lines.append(f"<@{uid}> — **{elo_val}** ELO ({g} games)")
    embed.add_field(name="🎯 ELO Ratings", value="\n".join(elo_lines), inline=False)

    embed.add_field(name="Confirmed", value="Nobody has confirmed this match yet.", inline=False)

    view = WargameMatchView(bot)
    mentions = " ".join(f"<@{uid}>" for uid in player_xids)

    await interaction.response.send_message(content=mentions, embed=embed, view=view)
    message = await interaction.original_response()

    matches_svc = WargameMatchesService()
    await matches_svc.create(
        guild_xid=interaction.guild.id,
        season_id=season.id,
        player_xids=player_xids,
        army_ids=army_ids,
        winner_xid=interaction.user.id if is_win else None,
        channel_xid=interaction.channel_id,
        message_xid=message.id,
    )

    # ── Pre-match ELO alert DMs (fire-and-forget) ─────────────────────────────
    await _send_wargame_elo_alert_dms(
        bot, interaction.guild.id, player_xids, elo_rows, game_system
    )
