from __future__ import annotations

"""Shared helpers used across league cogs (not a cog itself)."""

import logging
from typing import TYPE_CHECKING

import discord

from seer.database import DatabaseSession
from seer.models import LeagueDeck, LeagueProfile, LeagueSeason
from seer.services import LeagueConfigService, LeagueDecksService, LeagueMatchesService, LeagueSeasonsService
from seer.services.league_elo import SEAT_BASELINE_WIN_RATES, SEAT_LABELS

if TYPE_CHECKING:
    from seer import Seer

logger = logging.getLogger(__name__)

# Minimum ELO spread (max − min across all players) required to send private
# ELO matchup alert DMs.  The ELO ratings field is always shown.
ELO_ALERT_THRESHOLD = 100


def build_seat_positions(
    logger_xid: int,
    opponent_xids: list[int],
    my_seat: int | None,
) -> dict[int, int] | None:
    """Build a {user_xid: seat} dict from the logger's declared seat.

    If ``my_seat`` is None the caller hasn't provided seat info — return None
    so the ELO formula runs without seat correction.

    Convention: the three opponents are assigned to the remaining seats (in
    ascending order) based on the order they were listed in the command.
    e.g. my_seat=3, opponents=[Alice, Bob, Carol]
         → remaining seats 1,2,4 → Alice=1, Bob=2, Carol=4
    """
    if my_seat is None:
        return None
    remaining = sorted(s for s in range(1, 5) if s != my_seat)
    positions: dict[int, int] = {logger_xid: my_seat}
    for opp_xid, seat in zip(opponent_xids, remaining):
        positions[opp_xid] = seat
    return positions


async def log_match(
    bot: Seer,
    interaction: discord.Interaction,
    player_xids: list[int],
    is_win: bool,
    my_seat: int | None = None,
) -> None:
    """Create and post a match confirmation embed with Confirm/Dispute/Cancel buttons.

    player_xids[0] must be the user running the command (the winner / draw initiator).
    my_seat (1–4): the seat number the logging player occupied.  When provided
    the remaining players are assigned to the other seats in the order listed,
    and seat-bias ELO correction is applied on confirmation.
    """
    assert interaction.guild is not None

    # Deduplicate players
    if len(set(player_xids)) != len(player_xids):
        await interaction.response.send_message(
            "All players in a match must be unique.", ephemeral=True
        )
        return

    seasons_svc = LeagueSeasonsService()
    season = await seasons_svc.get_active(interaction.guild.id)
    if season is None:
        await interaction.response.send_message(
            "There is no active season. An admin must start one with `/season start`.",
            ephemeral=True,
        )
        return

    # Check if draws are allowed
    if not is_win:
        cfg_svc = LeagueConfigService()
        config = await cfg_svc.upsert(interaction.guild.id)
        if not config.enable_draws:
            await interaction.response.send_message(
                "Draws are currently disabled on this server.", ephemeral=True
            )
            return

    # Build seat positions from the logger's declared seat (may be None)
    seat_positions = build_seat_positions(
        logger_xid=player_xids[0],
        opponent_xids=player_xids[1:],
        my_seat=my_seat,
    )

    # Fetch each player's current deck
    decks_svc = LeagueDecksService()
    deck_ids: list[int | None] = []
    deck_labels: list[str] = []

    for uid in player_xids:
        profile = await decks_svc.get_profile(interaction.guild.id, uid)
        if profile.current_deck_id:
            deck = await decks_svc.get_by_id(profile.current_deck_id)
            deck_ids.append(deck.id if deck else None)
            if deck:
                if deck.deck_list:
                    deck_labels.append(f"[{deck.name}]({deck.deck_list})")
                else:
                    deck_labels.append(deck.name)
            else:
                deck_labels.append("Not specified")
        else:
            deck_ids.append(None)
            deck_labels.append("Not specified")

    # ── ELO lookup ────────────────────────────────────────────────────────────
    from seer.services.league_elo import LeagueEloService

    elo_svc = LeagueEloService()
    elo_map: dict[int, int] = await elo_svc.get_for_users(interaction.guild.id, player_xids)

    elo_values = list(elo_map.values())
    elo_spread = max(elo_values) - min(elo_values)
    notable_spread = elo_spread >= ELO_ALERT_THRESHOLD

    # Sort players by ELO descending for display
    sorted_by_elo = sorted(player_xids, key=lambda uid: elo_map.get(uid, 1500), reverse=True)

    # ── Build the embed ───────────────────────────────────────────────────────
    from seer.views import LeagueMatchView

    color = discord.Color.green() if is_win else discord.Color.blue()
    embed = discord.Embed(
        title="Match Confirmation",
        description=(
            "The match will be recorded as a **win** for the player who logged it."
            if is_win
            else "The match will be recorded as a **draw**."
        )
        + "\n\nClick below to confirm or dispute the match details.",
        color=color,
    )

    player_text = "\n".join(f"<@{uid}>" for uid in player_xids)
    deck_text = "\n".join(deck_labels)
    embed.add_field(name="Player", value=player_text, inline=True)
    embed.add_field(name="Deck", value=deck_text, inline=True)

    # Seat column — shown when seats were provided
    if seat_positions:
        seat_text = "\n".join(
            f"Seat {seat_positions[uid]}" for uid in player_xids
        )
        embed.add_field(name="Seat", value=seat_text, inline=True)

    # ELO ratings field — always shown so all players see the standings
    elo_lines = []
    for uid in sorted_by_elo:
        rating = elo_map.get(uid, 1500)
        crown = "👑 " if uid == sorted_by_elo[0] else ""
        elo_lines.append(f"{crown}<@{uid}> — **{rating}**")
    if notable_spread:
        elo_lines.append(f"*({elo_spread} ELO spread — alert DMs sent)*")
    if seat_positions:
        elo_lines.append("*Seat-bias ELO correction will be applied.*")
    embed.add_field(
        name="⚔️ ELO Ratings",
        value="\n".join(elo_lines),
        inline=False,
    )

    embed.add_field(name="Confirmed", value="Nobody has confirmed this match yet.", inline=False)

    view = LeagueMatchView(bot)
    mentions = " ".join(f"<@{uid}>" for uid in player_xids)

    await interaction.response.send_message(content=mentions, embed=embed, view=view)
    message = await interaction.original_response()

    # Persist the match record (including seat info)
    matches_svc = LeagueMatchesService()
    await matches_svc.create(
        guild_xid=interaction.guild.id,
        season_id=season.id,
        player_xids=player_xids,
        deck_ids=deck_ids,
        winner_xid=interaction.user.id if is_win else None,
        channel_xid=interaction.channel_id,
        message_xid=message.id,
        seat_positions=seat_positions,
    )

    # ── ELO matchup alert DMs ─────────────────────────────────────────────────
    # Only sent privately when the spread is notable; avoids noise for evenly
    # matched pods.  Both the favourite and the underdog(s) are notified.
    if notable_spread:
        await _send_elo_alert_dms(bot, player_xids, elo_map, sorted_by_elo, seat_positions)


async def _send_elo_alert_dms(
    bot: Seer,
    player_xids: list[int],
    elo_map: dict[int, int],
    sorted_by_elo: list[int],
    seat_positions: dict[int, int] | None,
) -> None:
    """Privately DM every player in the pod about the ELO spread."""
    top_uid = sorted_by_elo[0]
    top_elo = elo_map[top_uid]

    # Build the standings block once — reused in every player's DM
    standings_lines = []
    for rank, uid in enumerate(sorted_by_elo, start=1):
        rating = elo_map[uid]
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"#{rank}")
        seat_note = ""
        if seat_positions and uid in seat_positions:
            s = seat_positions[uid]
            bias = SEAT_BASELINE_WIN_RATES.get(s, 0.25) - 0.25
            sign = "+" if bias >= 0 else ""
            seat_note = f" *(seat {s}, {sign}{bias*100:.1f}%)*"
        standings_lines.append(f"{medal} <@{uid}> — **{rating} ELO**{seat_note}")
    standings_text = "\n".join(standings_lines)

    for uid in player_xids:
        my_elo = elo_map[uid]

        if uid == top_uid:
            status_text = (
                "🎯 You're the **highest-rated** player in this pod. "
                "The field will be gunning for you — don't underestimate the challenge."
            )
        else:
            gap = top_elo - my_elo
            status_text = (
                f"⬆️ You're facing <@{top_uid}> who is **{gap} ELO** above you. "
                "This is your chance to climb — an upset win earns bigger ELO gains."
            )

        # Add seat context if we have it
        seat_context = ""
        if seat_positions and uid in seat_positions:
            s = seat_positions[uid]
            label = SEAT_LABELS.get(s, f"Seat {s}")
            seat_context = (
                f"\n\n**Your seat:** {label}\n"
                "ELO gains and losses will be adjusted to account for your seat's "
                "statistical advantage or disadvantage."
            )

        embed = discord.Embed(
            title="⚔️ ELO Matchup Alert",
            description=(
                "Your match has a notable ELO spread across the pod. "
                f"Here's how the ratings stack up:{seat_context}"
            ),
            color=discord.Color.orange(),
        )
        embed.add_field(name="Pod ELO Rankings", value=standings_text, inline=False)
        embed.add_field(name="Your Situation", value=status_text, inline=False)
        embed.add_field(
            name="How ELO works here",
            value=(
                "Gains scale with the spread — beating higher-rated opponents earns more, "
                "losing to them costs less. "
                + (
                    "Seat position is also factored in: winning from seat 4 earns *more* "
                    "than winning from seat 1 with identical ratings."
                    if seat_positions
                    else "Tip: use the `/log my_seat:` option to enable seat-bias correction."
                )
            ),
            inline=False,
        )
        embed.set_footer(text="SouthSeer — Southside Studio and Hobbies")

        try:
            user = await bot.fetch_user(uid)
            await user.send(embed=embed)
        except Exception:
            pass  # DMs may be disabled; silently skip
