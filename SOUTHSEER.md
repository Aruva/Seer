# SouthSeer — Bot Description

SouthSeer is the custom Discord bot for **Southside Studio and Hobbies**, built to run competitive leagues and track results for **Magic: The Gathering** (Commander EDH and 60-card 1v1 formats) and **tabletop wargames** right inside your Discord server.

---

## Magic: The Gathering — Commander (EDH)

SouthSeer manages a full Commander league season — from the first match to the final standings.

- **Match logging** — Use `/log` to record a win or `/draw` for a draw. Tag your three opponents and the bot handles the rest.
- **ELO ratings** — Every player carries a live ELO rating that updates after each confirmed match. Ratings use a multiplayer formula tuned for 4-player pods, and optionally apply a **seat-bias correction** derived from 648 competitive EDH tournament games (Seat 1 wins ~31.5% of pods vs. ~20% for Seat 4).
- **ELO matchup alerts** — When a pod has a rating spread of 100+ points, SouthSeer privately DMs each player before the game, showing the full pod standings, each player's seat-win percentage, and whether they're the underdog or the favorite.
- **ELO confirmation DMs** — After all four players confirm a result, everyone gets a private DM showing exactly how their rating changed (e.g., 📈 +12 → 1547) and any seat correction that was applied.
- **Player profiles** — `/profile` shows your current ELO, tier (Newcomer → Champion), total games played, and win/draw/loss record.
- **Season leaderboards** — `/leaderboard` ranks eligible players by a configurable points formula (wins, losses, draws) with a minimum-games threshold.
- **Season management** — Admins use `/season start` and `/season end` to manage competitive seasons; historical seasons remain queryable.
- **Deck tracking** — Link and track the Commander decks you've played each season.
- **Unconfirmed match reminders** — SouthSeer automatically DMs players every 30 minutes when they have a match waiting for confirmation.

---

## Magic: The Gathering — 60-Card 1v1

Full league support for competitive 60-card formats. Each format is tracked independently with its own ELO, seasons, and leaderboard.

**Supported formats:** Standard · Pioneer · Modern · Legacy · Vintage

- **Match logging** — `/mlog` records a win; `/mdraw` records a draw. Select the format from a live autocomplete list.
- **ELO ratings** — Standard 1v1 ELO formula with K-factor tiers. Ratings per format are completely independent — your Modern ELO has no effect on your Legacy ELO.
- **ELO matchup alerts** — When a 100+ point spread exists, both players get a DM before the match showing current ratings and underdog/favourite status.
- **ELO confirmation DMs** — After both players confirm, each gets a private DM with their exact rating change (e.g., 📈 +18 → 1531).
- **Deck tracking** — `/mdeck create` and `/mdeck use` let players register decks with archetype labels and Moxfield/Archidekt links, recorded with every match.
- **Player profiles** — `/mprofile` shows your ELO, tier, active deck, and win/loss record for any format.
- **Season leaderboards** — `/mleaderboard` shows standings per format.
- **Season management** — `/mseason start` and `/mseason end` managed independently per format.

---

## Wargame League

The same structured league system extends to tabletop wargames — Warmachine/Hordes, Warhammer 40,000, or any custom game system the store configures.

- **Match logging** — `/wlog` records a win; `/wdraw` records a draw. Select the game system from a live autocomplete list.
- **ELO ratings** — Standard 1v1 ELO with K-factor tiers. Warmachine and 40K ratings are tracked independently.
- **ELO matchup alerts** — When two players with a 100+ point rating spread are matched, SouthSeer DMs both players before the game.
- **ELO confirmation DMs** — After both players confirm, each gets a private DM showing their exact rating change.
- **Game system configuration** — Admins use `/wgameconfig` to add or remove game systems and set point values for each.
- **Army tracking** — Players register and track the armies/factions they play.
- **Wargame profiles** — `/wprofile` shows ELO, tier, active army, win/loss record, and season points.
- **Wargame leaderboards** — `/wleaderboard` shows season standings filtered by game system.
- **Season management** — `/wseason start` and `/wseason end`, tracked independently per game system.

---

## At a Glance

| Feature | MTG Commander (EDH) | MTG 60-Card 1v1 | Wargames |
|---|---|---|---|
| Match logging (win/draw/loss) | ✅ | ✅ | ✅ |
| ELO ratings | ✅ (seat-corrected, 4-player) | ✅ (1v1, per format) | ✅ (1v1, per game system) |
| Pre-match ELO alerts | ✅ | ✅ | ✅ |
| Post-match ELO DMs | ✅ | ✅ | ✅ |
| Player profiles | ✅ | ✅ | ✅ |
| Deck/army tracking | ✅ | ✅ | ✅ |
| Season leaderboards | ✅ | ✅ | ✅ |
| Multi-season history | ✅ | ✅ | ✅ |
| Confirmation reminders | ✅ | ✅ | ✅ |
| Admin configuration | ✅ | ✅ | ✅ |

---

SouthSeer is self-hosted and runs entirely on Southside Studio and Hobbies' own server — your community's data stays yours.
