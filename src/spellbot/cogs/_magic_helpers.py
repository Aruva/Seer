from __future__ import annotations

"""Shared helpers for Magic: The Gathering 60-card 1v1 league cogs."""

import logging
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import discord

from spellbot.models import KNOWN_MAGIC_FORMATS
from spellbot.services.wargame_elo import WARGAME_ELO_ALERT_THRESHOLD

if TYPE_CHECKING:
    from spellbot import SpellBot

logger = logging.getLogger(__name__)

# ── Format helpers ────────────────────────────────────────────────────────────

FORMAT_ALIASES: dict[str, str] = {
    "std":      "standard",
    "pio":      "pioneer",
    "mod":      "modern",
    "leg":      "legacy",
    "vin":      "vintage",
    "vint":     "vintage",
}


def normalize_format(slug: str) -> str:
    key = slug.lower().strip()
    return FORMAT_ALIASES.get(key, key)


def display_format(fmt: str) -> str:
    return KNOWN_MAGIC_FORMATS.get(fmt, fmt.replace("-", " ").title())


# ── Valid deck list hosts ─────────────────────────────────────────────────────

VALID_DECK_LIST_HOSTS: frozenset[str] = frozenset({
    "moxfield.com",
    "archidekt.com",
    "tappedout.net",
    "mtggoldfish.com",
    "deckstats.net",
    "mtgtop8.com",
    "aetherhub.com",
    "manastack.com",
})


def validate_deck_url(url: str) -> bool:
    try:
        hostname = (urlparse(url).hostname or "").lower().removeprefix("www.")
        return hostname in VALID_DECK_LIST_HOSTS
    except Exception:
        return False


# ── Autocomplete ──────────────────────────────────────────────────────────────

async def magic_format_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[discord.app_commands.Choice[str]]:
    """Autocomplete for Magic format selection."""
    query = normalize_format(current) if current else ""
    results = []
    for slug, label in KNOWN_MAGIC_FORMATS.items():
        if not query or query in slug or query in label.lower():
            results.append(discord.app_commands.Choice(name=label, value=slug))
    return results[:25]


# ── ELO alert DMs ─────────────────────────────────────────────────────────────

async def _send_magic_elo_alert_dms(
    bot: SpellBot,
    player_xids: list[int],
    elo_rows: dict,
    fmt: str,
) -> None:
    """DM both players when ELO spread ≥ threshold."""
    fmt_label = display_format(fmt)
    elos = {uid: elo_rows[uid].elo for uid in player_xids}
    games = {uid: elo_rows[uid].games_played for uid in player_xids}

    sorted_players = sorted(player_xids, key=lambda uid: elos[uid], reverse=True)
    top_uid, low_uid = sorted_players[0], sorted_players[1]
    spread = elos[top_uid] - elos[low_uid]

    if spread < WARGAME_ELO_ALERT_THRESHOLD:
        return

    for uid in player_xids:
        opponent_uid = low_uid if uid == top_uid else top_uid
        if uid == top_uid:
            status = "⭐ **You are the higher-rated player** in this match."
        else:
            status = "🐉 **You are the underdog** — an upset win is worth more ELO."

        embed = discord.Embed(
            title=f"🃏 {fmt_label} — ELO Matchup Alert",
            description=(
                f"A match has been logged against <@{opponent_uid}>. "
                "Here are the current ratings:"
            ),
            color=discord.Color.orange(),
        )
        lines = []
        for p in sorted_players:
            g = games[p]
            tier = "provisional" if g < 30 else "standard" if g < 60 else "established"
            lines.append(f"<@{p}> — **{elos[p]}** ELO *(K: {tier}, {g} games)*")
        embed.add_field(name="Current Ratings", value="\n".join(lines), inline=False)
        embed.add_field(name="Rating Spread", value=f"{spread} points", inline=True)
        embed.add_field(name="Status", value=status, inline=False)
        embed.add_field(
            name="ℹ️ How ELO works",
            value=(
                "Your rating shifts based on how surprising the result is. "
                "Beating a higher-rated opponent earns more ELO. "
                "ELO updates once both players confirm."
            ),
            inline=False,
        )
        embed.set_footer(text="SouthSeer — Southside Studio and Hobbies")
        try:
            user = await bot.fetch_user(uid)
            await user.send(embed=embed)
        except Exception:
            pass


# ── Core match-logging helper ─────────────────────────────────────────────────

async def log_magic_match(
    bot: SpellBot,
    interaction: discord.Interaction,
    fmt: str,
    opponent: discord.Member,
    is_win: bool,
) -> None:
    """Create and post a 1v1 Magic match confirmation embed."""
    assert interaction.guild is not None

    fmt = normalize_format(fmt)

    if opponent.id == interaction.user.id:
        await interaction.response.send_message(
            "You cannot log a match against yourself.", ephemeral=True
        )
        return

    from spellbot.services import (
        WargameArmiesService,
        WargameConfigService,
        WargameEloService,
        WargameMatchesService,
        WargameSeasonsService,
    )

    seasons_svc = WargameSeasonsService()
    season = await seasons_svc.get_active(interaction.guild.id, fmt)
    fmt_label = display_format(fmt)
    if season is None:
        await interaction.response.send_message(
            f"There is no active {fmt_label} season. "
            "An admin must start one with `/mseason start`.",
            ephemeral=True,
        )
        return

    if not is_win:
        cfg_svc = WargameConfigService()
        config = await cfg_svc.upsert(interaction.guild.id, fmt)
        if not config.enable_draws:
            await interaction.response.send_message(
                "Draws are currently disabled on this server.", ephemeral=True
            )
            return

    player_xids = [interaction.user.id, opponent.id]

    # ELO lookup
    elo_svc = WargameEloService()
    elo_rows = await elo_svc.get_for_users(interaction.guild.id, player_xids, fmt)
    elos = {uid: elo_rows[uid].elo for uid in player_xids}

    # Active deck lookup
    armies_svc = WargameArmiesService()
    army_ids: list[int | None] = []
    deck_labels: list[str] = []

    for uid in player_xids:
        profile = await armies_svc.get_profile(interaction.guild.id, uid, fmt)
        if profile.current_army_id:
            deck = await armies_svc.get_by_id(profile.current_army_id)
            if deck:
                army_ids.append(deck.id)
                label = deck.name
                if deck.faction:
                    label += f" ({deck.faction})"
                deck_labels.append(f"[{label}]({deck.list_url})" if deck.list_url else label)
            else:
                army_ids.append(None)
                deck_labels.append("Not specified")
        else:
            army_ids.append(None)
            deck_labels.append("Not specified")

    from spellbot.views import MagicMatchView

    color = discord.Color.green() if is_win else discord.Color.blue()
    embed = discord.Embed(
        title=f"🃏 {fmt_label} — Match Confirmation",
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
    embed.add_field(name="Deck", value="\n".join(deck_labels), inline=True)

    elo_lines = []
    for uid in player_xids:
        g = elo_rows[uid].games_played
        elo_lines.append(f"<@{uid}> — **{elos[uid]}** ELO ({g} games)")
    embed.add_field(name="🎯 ELO Ratings", value="\n".join(elo_lines), inline=False)
    embed.add_field(name="Confirmed", value="Nobody has confirmed this match yet.", inline=False)

    view = MagicMatchView(bot)
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

    # Pre-match ELO alert DMs
    await _send_magic_elo_alert_dms(bot, player_xids, elo_rows, fmt)
