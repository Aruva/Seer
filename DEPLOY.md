# Deploying SouthSeer — Self-Hosted Docker Guide

## Prerequisites

- Docker Desktop (Windows/Mac) or Docker Engine (Linux) installed and running
- A Discord account with a bot application created at https://discord.com/developers/applications

---

## Step 1 — Create and configure your Discord bot

1. Go to https://discord.com/developers/applications and open your application.
2. Navigate to **Bot**.
   - Click **Reset Token** to generate a new token (especially if you ever shared the old one).
   - Copy the token — you'll need it in Step 3.
   - Under **Privileged Gateway Intents**, enable:
     - **Server Members Intent** (needed for member lookups in dispute threads)
     - **Message Content Intent** (needed for persistent view handling)
3. Navigate to **General Information** and copy your **Application ID**.

---

## Step 2 — Invite the bot to your server

Use this URL (replace `YOUR_APPLICATION_ID`):

```
https://discord.com/api/oauth2/authorize
  ?client_id=YOUR_APPLICATION_ID
  &permissions=328565085248
  &scope=applications.commands%20bot
```

Permissions included: View Channels, Send Messages, Create Public Threads,
Send Messages in Threads, Manage Messages, Manage Threads, Embed Links,
Read Message History, Use Slash Commands, Use External Emojis.

---

## Step 3 — Configure your .env file

Open `.env` in the project root and fill in the three required values:

```
BOT_TOKEN=            ← paste your bot token from Step 1
BOT_APPLICATION_ID=   ← paste your Application ID from Step 1
DEBUG_GUILD=          ← right-click your server icon in Discord → Copy Server ID
```

**How to find your Server ID:**
Enable Developer Mode in Discord (User Settings → Advanced → Developer Mode),
then right-click your server icon and choose "Copy Server ID".

---

## Step 4 — Build and start

Open a terminal in the project root folder (where `docker-compose.yml` lives) and run:

```bash
docker compose up --build -d
```

What happens behind the scenes:
1. Docker builds the SouthSeer image from the `Dockerfile`.
2. PostgreSQL starts and waits until healthy.
3. The **migrate** service runs all pending Alembic migrations automatically.
4. The **bot** service starts once migrations complete.

On first run the image build takes 2–5 minutes. Subsequent starts are fast.

---

## Step 5 — Verify it's running

```bash
docker compose logs -f bot
```

You should see lines like:
```
will start southseer...
running without ddtrace...
starting southseer now!
Logged in as Seer#XXXX
```

Press `Ctrl+C` to stop watching logs (the bot keeps running).

---

## Day-to-day commands

| What you want to do | Command |
|---------------------|---------|
| Start everything | `docker compose up -d` |
| Stop everything | `docker compose down` |
| View bot logs (live) | `docker compose logs -f bot` |
| Restart just the bot | `docker compose restart bot` |
| Pull a code update & rebuild | `docker compose up --build -d` |
| Run migrations manually | `docker compose run --rm migrate` |

---

## Updating the bot after code changes

```bash
docker compose up --build -d
```

This rebuilds the image with your latest code, runs any new migrations, and
restarts the bot. Database data is persisted in the `db_data` Docker volume
and is never lost on rebuilds.

---

## Backups

Your database lives in a Docker volume named `db_data`. To back it up:

```bash
docker compose exec db pg_dump -U postgres southseer > southseer_backup.sql
```

To restore from a backup:

```bash
cat southseer_backup.sql | docker compose exec -T db psql -U postgres southseer
```

---

## Troubleshooting

**Bot won't start / "BOT_TOKEN is not set"**
→ Make sure `.env` has `BOT_TOKEN=` filled in (no quotes around the value).

**Slash commands don't appear in Discord**
→ Make sure `DEBUG_GUILD=` is set to your server's ID. Without it, global
  command registration can take up to an hour. Restart the bot after setting it.

**"Cannot connect to database"**
→ The db service may still be starting. Run `docker compose logs db` to check.
  If the volume is corrupted: `docker compose down -v` (⚠️ deletes all data),
  then `docker compose up --build -d`.

**Migration failed**
→ Run `docker compose logs migrate` to see the error. Common causes: the
  database container wasn't ready yet (re-running `docker compose up -d` usually
  fixes it), or a migration script has a syntax error.
