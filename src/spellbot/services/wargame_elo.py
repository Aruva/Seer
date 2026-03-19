from __future__ import annotations

"""ELO rating service for the wargame (1v1) league.

Standard two-player ELO formula:

    expected = 1 / (1 + 10 ^ ((opponent_elo - player_elo) / 400))
    actual   = 1.0 (win) | 0.5 (draw) | 0.0 (loss)
    Δ ELO    = K × (actual − expected)

No seat-bias correction is applied because wargame matches are 1v1 and
turn order is handled by game-specific mechanisms (coin flip, scenario
rules, etc.) rather than a statistically measurable structural advantage.

K-factor tiers (shared with EDH league):
    < 30 games  → K = 32  (provisional — larger swings while settling in)
    30–59 games → K = 24
    ≥ 60 games  → K = 16  (established — stable rating)

ELO is floored at 100 and scoped per (guild, game_system) so a player's
Warmachine and 40K ratings are independent.
"""

from asgiref.sync import sync_to_async

from spellbot.database import DatabaseSession
from spellbot.models import WargameElo

DEFAULT_ELO = 1500
ELO_FLOOR = 100
WARGAME_ELO_ALERT_THRESHOLD = 100  # DM players when spread ≥ this many points

# ── K-factor tiers ────────────────────────────────────────────────────────────
_K_PROVISIONAL = 32
_K_STANDARD = 24
_K_ESTABLISHED = 16


def _k_factor(games_played: int) -> int:
    if games_played < 30:
        return _K_PROVISIONAL
    if games_played < 60:
        return _K_STANDARD
    return _K_ESTABLISHED


def _expected_score(rating_a: int, rating_b: int) -> float:
    """Standard ELO expected score for player A against player B."""
    return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))


def calculate_wargame_elo_deltas(
    elo_map: dict[int, int],
    games_map: dict[int, int],
    winner_xid: int | None,
) -> dict[int, int]:
    """Compute integer ELO delta for each player in a 1v1 match.

    Parameters
    ----------
    elo_map:    {user_xid: current_elo}  — exactly 2 entries
    games_map:  {user_xid: games_played} — for K-factor lookup
    winner_xid: xid of the winner, or None for a draw

    Returns
    -------
    {user_xid: delta}  — deltas sum to 0 (zero-sum preserved)
    """
    player_ids = list(elo_map.keys())
    if len(player_ids) != 2:
        return {}

    a, b = player_ids
    elo_a, elo_b = elo_map[a], elo_map[b]

    exp_a = _expected_score(elo_a, elo_b)
    exp_b = 1.0 - exp_a

    if winner_xid is None:
        # Draw
        actual_a, actual_b = 0.5, 0.5
    elif winner_xid == a:
        actual_a, actual_b = 1.0, 0.0
    else:
        actual_a, actual_b = 0.0, 1.0

    k_a = _k_factor(games_map.get(a, 0))
    k_b = _k_factor(games_map.get(b, 0))

    delta_a = int(round(k_a * (actual_a - exp_a)))
    delta_b = int(round(k_b * (actual_b - exp_b)))

    return {a: delta_a, b: delta_b}


# ── Service ───────────────────────────────────────────────────────────────────

class WargameEloService:
    """CRUD and calculation helpers for wargame ELO ratings."""

    @sync_to_async()
    def get_for_users(
        self,
        guild_xid: int,
        user_xids: list[int],
        game_system: str,
    ) -> dict[int, WargameElo]:
        """Return {user_xid: WargameElo} for each user, creating rows as needed."""
        rows: dict[int, WargameElo] = {}
        for uid in user_xids:
            row = (
                DatabaseSession.query(WargameElo)
                .filter(
                    WargameElo.guild_xid == guild_xid,
                    WargameElo.user_xid == uid,
                    WargameElo.game_system == game_system,
                )
                .one_or_none()
            )
            if row is None:
                row = WargameElo(
                    guild_xid=guild_xid,
                    user_xid=uid,
                    game_system=game_system,
                    elo=DEFAULT_ELO,
                    games_played=0,
                )
                DatabaseSession.add(row)
                DatabaseSession.flush()
            rows[uid] = row
        return rows

    @sync_to_async()
    def get_for_user(
        self,
        guild_xid: int,
        user_xid: int,
        game_system: str,
    ) -> WargameElo:
        """Return (or create) the WargameElo row for a single user."""
        row = (
            DatabaseSession.query(WargameElo)
            .filter(
                WargameElo.guild_xid == guild_xid,
                WargameElo.user_xid == user_xid,
                WargameElo.game_system == game_system,
            )
            .one_or_none()
        )
        if row is None:
            row = WargameElo(
                guild_xid=guild_xid,
                user_xid=user_xid,
                game_system=game_system,
                elo=DEFAULT_ELO,
                games_played=0,
            )
            DatabaseSession.add(row)
            DatabaseSession.flush()
        return row

    @sync_to_async()
    def update_for_match(
        self,
        guild_xid: int,
        player_xids: list[int],
        game_system: str,
        winner_xid: int | None,
    ) -> dict[int, tuple[int, int, int]]:
        """Apply ELO deltas and return {uid: (delta, old_elo, new_elo)}."""
        rows: dict[int, WargameElo] = {}
        for uid in player_xids:
            row = (
                DatabaseSession.query(WargameElo)
                .filter(
                    WargameElo.guild_xid == guild_xid,
                    WargameElo.user_xid == uid,
                    WargameElo.game_system == game_system,
                )
                .one_or_none()
            )
            if row is None:
                row = WargameElo(
                    guild_xid=guild_xid,
                    user_xid=uid,
                    game_system=game_system,
                    elo=DEFAULT_ELO,
                    games_played=0,
                )
                DatabaseSession.add(row)
                DatabaseSession.flush()
            rows[uid] = row

        elo_map = {uid: rows[uid].elo for uid in player_xids}
        games_map = {uid: rows[uid].games_played for uid in player_xids}
        deltas = calculate_wargame_elo_deltas(elo_map, games_map, winner_xid)

        results: dict[int, tuple[int, int, int]] = {}
        for uid, delta in deltas.items():
            old_elo = rows[uid].elo
            new_elo = max(ELO_FLOOR, old_elo + delta)
            rows[uid].elo = new_elo
            rows[uid].games_played += 1
            results[uid] = (delta, old_elo, new_elo)

        DatabaseSession.commit()
        return results

    @sync_to_async()
    def get_leaderboard(
        self, guild_xid: int, game_system: str, limit: int = 10
    ) -> list[WargameElo]:
        return (
            DatabaseSession.query(WargameElo)
            .filter(
                WargameElo.guild_xid == guild_xid,
                WargameElo.game_system == game_system,
                WargameElo.games_played > 0,
            )
            .order_by(WargameElo.elo.desc())
            .limit(limit)
            .all()
        )
