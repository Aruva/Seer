# Discord Post — SouthSeer Bot Introduction
# Copy each message block separately into Discord (each block = one message).
# The horizontal rules (---) mark where one message ends and the next begins.
# Formatting uses Discord markdown.
================================================================================


--- MESSAGE 1 ---

# 🔮 Meet SouthSeer — Your League Companion

Hey everyone! We've got a custom bot running in this server called **SouthSeer**, built specifically for Southside Studio and Hobbies. It handles everything for our competitive leagues — **Magic: The Gathering** (Commander EDH and 60-card formats) and **tabletop wargames** — without ever leaving Discord.

Here's what it does and how to use it. Read through once and you'll be set for every season going forward.

> 📬 **Important:** SouthSeer sends match alerts and results **via DM**. Make sure your Discord privacy settings allow DMs from server members, and that **Embeds and link previews** is enabled in your Chat settings. If you're not getting DMs, that's the first thing to check.


--- MESSAGE 2 ---

## ⚔️ Magic: The Gathering Commander (EDH) — How It Works

SouthSeer tracks your wins, draws, ELO rating, and season standing for every Commander pod you play.

**Logging a match**
After your game, the winner runs:
`/log player1:@name player2:@name player3:@name`

For draws, anyone in the pod runs:
`/draw player1:@name player2:@name player3:@name`

That posts a **confirmation embed** in the channel. All four players must click ✅ Confirm before the result locks in. Until everyone confirms, ELO doesn't move — SouthSeer will DM reminders every 30 minutes to anyone who hasn't confirmed yet.

**Optional: Seat tracking**
If you want the most accurate ELO, include your seat number when logging:
`/log player1:@name player2:@name player3:@name my_seat:2`

List your opponents in the order they occupy the remaining seats (if you're seat 2, list seat 1, seat 3, seat 4 in that order). This unlocks **seat-bias correction** — statistically, seat 1 wins about 31.5% of cEDH pods while seat 4 wins only 20.2%. SouthSeer adjusts ELO gains and losses to compensate, so winning from a disadvantaged seat is worth more.

**Disputing a result**
If something's wrong, any player can click ⚠️ Dispute. This opens a private thread where you can sort it out. The original logger can cancel the match entirely with ❌ Cancel.


--- MESSAGE 3 ---

## 📊 Commander (EDH) — ELO Ratings

Everyone starts at **1500 ELO**. It goes up when you win and down when you lose, scaled by how surprising the result was. Beating three higher-rated players earns more than beating three lower-rated ones.

**Tiers**
- Newcomer — getting started
- Developing — building a track record
- Veteran — 1500+, established
- Expert — 1600+
- Champion — 1700+

**Pre-match alerts**
When a pod has a 100+ point rating spread, SouthSeer DMs all four players *before* the match confirming is complete, showing standings like:
```
@Player1 — 1712 ELO (Seat 1, +6.5% win rate)
@Player2 — 1603 ELO (Seat 2, -0.8% win rate)
@Player3 — 1541 ELO (Seat 3, -0.9% win rate)
@Player4 — 1498 ELO (Seat 4, -4.8% win rate) ← You are the underdog
```
Beating a heavily favoured pod is worth noticing. The bot makes sure everyone knows the stakes.

**Post-match ELO DMs**
Once all four players confirm, everyone gets a private DM like:
```
📈 +18 → 1516 ELO  *(seat 4 correction applied)*
```

**Checking your rating**
`/profile` — shows your ELO, tier, games played, and full win/draw/loss record


--- MESSAGE 4 ---

## 🏆 Commander (EDH) — Seasons, Leaderboards & Decks

Seasons are how we run structured competition. Each season has its own standings, and old seasons stay on record so you can look back.

**Leaderboard**
`/leaderboard` — current season standings, ranked by points
`/leaderboard season:Season 1` — look up a past season

Points are calculated from your confirmed wins, draws, and losses. A minimum number of games is required to appear on the board.

**Season info**
`/season info` — details on the current active season
`/season info name:Season 1` — look up any past season

**Deck tracking**
`/deck add url:https://moxfield.com/your-deck name:Thrasios Combo` — register a deck
`/deck use name:Thrasios Combo` — set it as your active deck for the season
When you log matches, your active deck is recorded. At end of season you'll have a full record of what you played.


--- MESSAGE 5 ---

## 🃏 Magic: The Gathering 60-Card 1v1 — How It Works

SouthSeer runs full 1v1 competitive leagues for the classic 60-card formats. Each format is tracked separately — your Modern ELO has nothing to do with your Legacy ELO.

**Supported formats:** Standard · Pioneer · Modern · Legacy · Vintage

**Logging a match**
After your game, the winner runs:
`/mlog format:Modern opponent:@name`

For draws:
`/mdraw format:Modern opponent:@name`

The format field has **autocomplete** — just type "mod", "pio", "leg" etc. Both players click ✅ Confirm on the embed. ELO updates only after both players confirm.

**Your deck**
Register your deck before your first match so it gets recorded:
`/mdeck create format:Modern name:Temur Rhinos archetype:Crashcade list_url:https://moxfield.com/...`
`/mdeck use format:Modern name:Temur Rhinos`

You can swap decks between matches. Each result is linked to whatever deck you had active at the time.


--- MESSAGE 6 ---

## 📊 MTG 60-Card — ELO Ratings

Same ELO system as everything else in SouthSeer, tuned for 1v1.

Everyone starts at **1500 ELO** per format. K-factor tiers work the same way:
- First 30 games: larger swings while you're finding your level
- Games 30–59: medium swings
- 60+ games: smaller, stable swings

**Pre-match alerts**
When you log a match against someone 100+ ELO points away, both players get a private DM:
```
🃏 Modern — ELO Matchup Alert

@Opponent — 1621 ELO (K-factor: standard, 38 games)
@You — 1489 ELO (K-factor: provisional, 14 games)

Rating Spread: 132 points
🐉 You are the underdog — an upset win is worth more ELO.
```

**Post-match ELO DMs**
After both players confirm:
```
📈 +24 → 1513 ELO  (was 1489)
```

**Checking your rating**
`/mprofile format:Modern` — shows ELO, tier, active deck, win/loss record, and season points


--- MESSAGE 7 ---

## 🏆 MTG 60-Card — Seasons & Leaderboards

`/mleaderboard format:Modern` — current season standings
`/mleaderboard format:Legacy` — Legacy standings (fully separate)
`/mseason info format:Modern` — details on the active season

Each format has its own independent season. Admins start and end them with:
`/mseason start format:Modern name:Season 1`
`/mseason end format:Modern`


--- MESSAGE 8 ---

## 🎖️ Wargame League — How It Works

The same league system runs for **Warmachine/Hordes** and **Warhammer 40K** out of the box, and admins can add any other game system. Your ELO and standings for each game are tracked independently.

**Logging a match**
After your game, the winner runs:
`/wlog game_system:Warmachine opponent:@name`

For draws:
`/wdraw game_system:Warmachine opponent:@name`

The game system field has **autocomplete** — just start typing "warm" or "40k" and it fills in. Common aliases work too: `40k`, `wm`, `wmh`, `warhammer` all resolve automatically.

Both players click ✅ Confirm. Same drill — the match doesn't lock until both confirm.

**Your army**
Before your first match, set your active army so it gets recorded with your results:
`/army create game_system:Warmachine name:Cygnar faction:Storm Division`
`/army use game_system:Warmachine name:Cygnar`

You can register multiple armies and swap between them.


--- MESSAGE 9 ---

## 📊 Wargames — ELO Ratings & Leaderboards

Every player has a separate ELO for each game system. Your Warmachine rating has nothing to do with your 40K rating.

Same K-factor tiers as MTG: provisional → standard → established as you accumulate games.

**Pre-match alerts**
When you log a match against someone 100+ ELO points away, both players get a DM before confirming:
```
⚔️ Warmachine — ELO Matchup Alert

@Opponent — 1634 ELO (K-factor: standard, 44 games)
@You — 1491 ELO (K-factor: provisional, 18 games)

Rating Spread: 143 points
🐉 You are the underdog — an upset win is worth more ELO.
```

**Post-match ELO DMs**
After both players confirm:
```
📈 +21 → 1512 ELO  (was 1491)
```

**Checking your rating**
`/wprofile game_system:Warmachine` — ELO, tier, active army, win/loss record, and season points

**Leaderboards & seasons**
`/wleaderboard game_system:Warmachine` — current season standings
`/wleaderboard game_system:Warhammer 40K` — 40K standings
`/wseason info game_system:Warmachine` — season details


--- MESSAGE 10 ---

## 📋 Quick Command Reference

**MTG Commander (EDH)**
`/log` — log a 4-player win
`/draw` — log a 4-player draw
`/profile` — your ELO, tier, and stats
`/leaderboard` — season standings
`/season info` — active season details
`/deck add` — register a Commander deck
`/deck use` — set your active deck

**MTG 60-Card 1v1**
`/mlog` — log a win (format + opponent)
`/mdraw` — log a draw
`/mprofile` — your ELO, tier, deck, and stats
`/mleaderboard` — season standings by format
`/mseason info` — active season details
`/mdeck create` — register a 60-card deck
`/mdeck use` — set your active deck

**Wargames**
`/wlog` — log a win (game system + opponent)
`/wdraw` — log a draw
`/wprofile` — your ELO, tier, army, and stats
`/wleaderboard` — season standings by game system
`/wseason info` — active season details
`/army create` — register an army
`/army use` — set your active army

**Tips**
- All commands are slash commands — type `/` and look for SouthSeer's commands
- Format and game system fields support autocomplete (type "mod", "40k", "wm", etc.)
- ELO only updates after **all players confirm** — don't leave your opponents hanging!
- If you're not getting DMs, check Discord Settings → Privacy & Safety → allow DMs from server members, and Settings → Chat → enable embeds

Questions? Ask in the server. Good luck out there. 🎲
