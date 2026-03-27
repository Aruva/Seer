from __future__ import annotations

"""ELO rating service for the EDH league.

Seat-bias correction
--------------------
Competitive cEDH tournament data (648 pods, Silicon Dynasty / Eminence Events
dataset) shows statistically significant turn-order advantages:

  Seat 1: 31.5%  (+6.5 pp vs. the fair 25%)   ← advantaged
  Seat 2: 24.2%  (-0.8 pp)                     ← near-neutral
  Seat 3: 24.1%  (-0.9 pp)                     ← near-neutral
  Seat 4: 20.2%  (-4.8 pp vs. the fair 25%)   ← disadvantaged

(Source: topdeck.gg/articles/first-player-adv-silicon-dynasty)

The seat corrections sum to zero, so the ELO zero-sum property is preserved.
The formula applied per player is:

    Δ ELO = K × (actual_score − ELO_expected_score − seat_correction)

where seat_correction = baseline_win_rate(seat) − (1/N) for an N-player game.

Effect:
  • A seat-4 winner gains *more* ELO than a seat-1 winner with equal ratings,
    because they overcame a larger statistical disadvantage.
  • A seat-4 loser loses *less* ELO than a seat-1 loser.
  • When seat data is unavailable (legacy matches or untracked games) the
    correction is simply skipped and the standard formula applies.
"""

from asgiref.sync import sync_to_async

from seer.database import DatabaseSession
from seer.models import LeagueElo

DEFAULT_ELO = 1500
ELO_FLOOR = 100

# ── Seat-bias constants (4-player cEDH tournament data, n=648 pods) ──────────
# Observed win rates by seat position.  Values normalise to exactly 1.0 so
# the correction terms sum to zero, preserving ELO zero-sum.
SEAT_BASELINE_WIN_RATES: dict[int, float] = {
    1: 0.315,
    2: 0.242,
    3: 0.241,
    4: 0.202,
}

# Human-readable label used in embeds/DMs
SEAT_LABELS: dict[int, str] = {
    1: "Seat 1 (highest advantage, +6.5%)",
    2: "Seat 2 (near-neutral, -0.8%)",
    3: "Seat 3 (near-neutral, -0.9%)",
    4: "Seat 4 (highest disadvantage, -4.8%)",
}

# ── K-factor tiers ────────────────────────────────────────────────────────────
_K_PROVISIONAL = 32   # fewer than 30 games — larger swings while settling in
_K_STANDARD = 24      # 30–59 games
_K_ESTABLISHED = 16   # 60+ games — rating is stable


def _k_factor(games_played: int) -> int:
    if games_played < 30:
        return _K_PROVISIONAL
    if games_played < 60:
        return _K_STANDARD
    return _K_ESTABLISHED


def _expected_score(rating_a: int, rating_b: int) -> float:
    """Standard ELO expected score for player A against player B."""
    return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))


def calculate_elo_deltas(
    elo_map: dict[int, int],
    games_map: dict[int, int],
    winner_xid: int | None,
    seat_positions: dict[int, int] | None = None,
) -> dict[int, int]:
    """Compute integer ELO delta for each player in a multiplayer match.

    Parameters
    ----------
    elo_map:        {user_xid: current_elo}
    games_map:      {user_xid: games_played}  (for K-factor)
    winner_xid:     xid of the winner, or None for a draw
    seat_positions: {user_xid: seat_number 1–4}, optional.  When provided
                    and all four seats are covered, the seat-bias correction
                    is applied.  Ignored for non-4-player pods.

    Formula (per player i in seat S):
        actual   = 1.0 if winner, 0.0 if loser, 1/N if draw
        expected = average pairwise ELO expected score vs. every opponent
        seat_corr = SEAT_BASELINE_WIN_RATES[S] − (1/N)   (zero when unknown)
        Δ = K × (actual − expected − seat_corr)

    The seat correction raises the bar for advantaged seats and lowers it for
    disadvantaged ones, making upsets from seat 4 worth more ELO.
    Sum of all Δ across the pod is always 0 (zero-sum preserved).
    """
    player_ids = list(elo_map.keys())
    n = len(player_ids)
    if n < 2:
        return {}

    # Seat correction is only valid when we have all 4 seats in a 4-player pod
    use_seat_correction = (
        seat_positions is not None
        and n == 4
        and all(uid in seat_positions for uid in player_ids)
        and sorted(seat_positions[uid] for uid in player_ids) == [1, 2, 3, 4]
    )

    deltas: dict[int, float] = {}
    for uid in player_ids:
        # Actual score
        if winner_xid is None:
            actual = 1.0 / n
        elif uid == winner_xid:
            actual = 1.0
        else:
            actual = 0.0

        # ELO expected score (average pairwise vs. all opponents)
        expected = (
            sum(
                _expected_score(elo_map[uid], elo_map[opp])
                for opp in player_ids
                if opp != uid
            )
            / (n - 1)
        )

        # Seat correction: positive for advantaged seats, negative for disadvantaged
        seat_corr = 0.0
        if use_seat_correction and seat_positions is not None:
            seat = seat_positions[uid]
            seat_corr = SEAT_BASELINE_WIN_RATES.get(seat, 1.0 / n) - (1.0 / n)

        k = _k_factor(games_map.get(uid, 0))
        deltas[uid] = k * (actual - expected - seat_corr)

    return {uid: round(d) for uid, d in deltas.items()}


class LeagueEloService:
    """Manages per-guild ELO ratings for the EDH league."""

    @sync_to_async()
    def get_for_users(
        self, guild_xid: int, user_xids: list[int]
    ) -> dict[int, int]:
        """Return {user_xid: elo} for the given users.

        Players who have never played are returned with DEFAULT_ELO (1500).
        """
        rows = (
            DatabaseSession.query(LeagueElo)
            .filter(
                LeagueElo.guild_xid == guild_xid,
                LeagueElo.user_xid.in_(user_xids),
            )
            .all()
        )
        result = {uid: DEFAULT_ELO for uid in user_xids}
        for row in rows:
            result[row.user_xid] = row.elo
        return result

    @sync_to_async()
    def get_for_user(self, guild_xid: int, user_xid: int) -> tuple[int, int]:
        """Return (elo, games_played) for a single player."""
        row = (
            DatabaseSession.query(LeagueElo)
            .filter(
                LeagueElo.guild_xid == guild_xid,
                LeagueElo.user_xid == user_xid,
            )
            .one_or_none()
        )
        if row is None:
            return DEFAULT_ELO, 0
        return row.elo, row.games_played

    @sync_to_async()
    def update_for_match(
        self,
        guild_xid: int,
        winner_xid: int | None,
        player_xids: list[int],
        seat_positions: dict[int, int] | None = None,
    ) -> dict[int, dict[str, int]]:
        """Apply ELO updates for a completed, fully confirmed match.

        Parameters
        ----------
        seat_positions: {user_xid: seat_number 1–4}
            When provided, seat-bias correction is applied.  Pass None to
            use the plain formula (e.g. for historical / untracked seats).

        Returns {user_xid: {"old": int, "new": int, "delta": int}}.
        """
        # Fetch or create an ELO row for every player
        rows: dict[int, LeagueElo] = {}
        for uid in player_xids:
            row = (
                DatabaseSession.query(LeagueElo)
                .filter(
                    LeagueElo.guild_xid == guild_xid,
                    LeagueElo.user_xid == uid,
                )
                .one_or_none()
            )
            if row is None:
                row = LeagueElo(
                    guild_xid=guild_xid,
                    user_xid=uid,
                    elo=DEFAULT_ELO,
                    games_played=0,
                )
                DatabaseSession.add(row)
                DatabaseSession.flush()
            rows[uid] = row

        elo_map = {uid: rows[uid].elo for uid in player_xids}
        games_map = {uid: rows[uid].games_played for uid in player_xids}
        deltas = calculate_elo_deltas(elo_map, games_map, winner_xid, seat_positions)

        result: dict[int, dict[str, int]] = {}
        for uid in player_xids:
            old_elo = rows[uid].elo
            delta = deltas.get(uid, 0)
            new_elo = max(ELO_FLOOR, old_elo + delta)
            rows[uid].elo = new_elo
            rows[uid].games_played += 1
            result[uid] = {"old": old_elo, "new": new_elo, "delta": delta}

        DatabaseSession.commit()
        return result

    @sync_to_async()
    def get_leaderboard(self, guild_xid: int) -> list[dict[str, int]]:
        """Return ELO standings for the guild, sorted best-first.

        Each entry: {user_xid, elo, games_played}
        """
        rows = (
            DatabaseSession.query(LeagueElo)
            .filter(LeagueElo.guild_xid == guild_xid)
            .order_by(LeagueElo.elo.desc())
            .all()
        )
        return [
            {"user_xid": r.user_xid, "elo": r.elo, "games_played": r.games_played}
            for r in rows
        ]
