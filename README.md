# Seer

A Discord bot for running competitive leagues and tracking results — built for **Magic: The Gathering**, **tabletop wargames**, and **small community shops**.

---

## Acknowledgments

SouthSeer is built on the foundation of [Seer](https://github.com/Southsidestudio/Seer) by **Amy Troschinetz**. The original Seer is a beautifully engineered Discord bot for organizing Magic: The Gathering games via SpellTable, and it served as the foundation for everything SouthSeer has become. The original architecture — the migration system, the service layer, the cog structure, the persistent view pattern — all of that is Amy's work. SouthSeer would not exist without it.

SouthSeer is released under the [MIT License](LICENSE.md), the same license as the original Seer project, and we are deeply grateful for the open-source community that makes projects like this possible.

---

## About Us

Seer is built and maintained by **Southside Studio and Hobbies**, a veteran-owned small business. I'm Justin — a hobby developer with a degree in Engineering who spends most of his time painting miniatures and shuffling cardboard. Seer is my first app, born out of wanting a better way to run leagues on our local game store's Discord server.

What started as "let me just add a leaderboard" turned into a full-featured league tracker for three different game systems, an ELO rating engine, and now a shop system. That's how these things go.

---

## What Seer Does

Seer tracks competitive play across three game systems and provides a built-in shop for small Discord-based stores.

### Magic: The Gathering — Commander (EDH)

4-player pod league management with match logging, ELO ratings (including an optional seat-bias correction derived from 648 tournament games), deck tracking, seasons, leaderboards, and automatic confirmation reminders.

**Commands:** `/log`, `/draw`, `/profile`, `/leaderboard`, `/season`, `/deck`

### Magic: The Gathering — 60-Card 1v1

Dedicated support for Standard, Pioneer, Modern, Legacy, and Vintage. Each format has its own independent ELO rating, seasons, and leaderboard. Deck tracking with archetype labels and links to Moxfield, Archidekt, and other deck builders.

**Commands:** `/mlog`, `/mdraw`, `/mprofile`, `/mleaderboard`, `/mseason`, `/mdeck`

### Tabletop Wargames

Flexible system supporting Warhammer 40K, Age of Sigmar, Warmachine/Hordes, or any custom game system. 1v1 ELO ratings tracked independently per game system, army registration, and per-system leaderboards.

**Commands:** `/wlog`, `/wdraw`, `/wprofile`, `/wleaderboard`, `/wseason`, `/wgameconfig`

### Discord Shop

A lightweight storefront for small hobby businesses. Post product listings with images and prices, let customers order with a button click, track inventory and order status, and handle fulfillment — all inside Discord. Payment is handled externally (PayPal, Venmo, cash, etc.).

**Commands:** `/shop list`, `/shop order`, `/shop status`, `/shopadmin add`, `/shopadmin fulfill`, `/shopadmin post`

---

## Shared Features

All three game systems include:

- **ELO ratings** with K-factor tiers (Newcomer → Champion)
- **Pre-match alerts** — DMs both players when the rating spread is 100+ points
- **Post-match DMs** — Shows exact ELO change after confirmation
- **Persistent buttons** — Confirm/dispute/cancel buttons survive bot restarts
- **Season management** — Start, end, and query historical seasons
- **Deck/army tracking** — Register and track what you play
- **Leaderboards** — Configurable point formulas with minimum-game thresholds

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- A Discord bot token ([Developer Portal](https://discord.com/developers/applications))

### Setup

1. Clone this repository
2. Copy the example environment file and fill in your bot token:
   ```
   cp .env.example .env
   ```
3. Edit `.env` with your `BOT_TOKEN`, `BOT_APPLICATION_ID`, and `DEBUG_GUILD`
4. Start the bot:
   ```
   docker compose up --build -d
   ```

The bot will automatically initialize the database, run migrations, and connect to Discord. Slash commands register instantly to your `DEBUG_GUILD` server.

### Discord Setup

Your bot application needs **Privileged Gateway Intents** enabled in the Developer Portal (Presence, Server Members, Message Content). Invite the bot with both `bot` and `applications.commands` OAuth2 scopes.

---

## Architecture

SouthSeer inherits Seer's clean layered architecture:

- **Cogs** — Discord command handlers (one file per command group)
- **Services** — Business logic and database operations
- **Models** — SQLAlchemy ORM models
- **Views** — Persistent Discord UI components (buttons, modals)
- **Migrations** — Alembic database versioning

The bot runs as a Docker Compose stack: PostgreSQL database → Alembic migration runner → Discord bot.

---

## License

SouthSeer is released under the [MIT License](LICENSE.md), the same license as the original Seer project.

**Original work:** Copyright (c) Amy Troschinetz
**Modified work:** Copyright (c) Southside Studio and Hobbies
