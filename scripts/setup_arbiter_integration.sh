#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# setup_arbiter_integration.sh
#
# One-time setup to:
#   1. Run the Alembic migration (creates the infractions table)
#   2. Insert an API token scoped for infraction + player endpoints
#
# Usage (from the seer-main directory):
#   bash scripts/setup_arbiter_integration.sh
#
# Prerequisites:
#   - Docker Compose services are running (at least db)
#   - Or: a local Postgres is running
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

API_TOKEN="ZRZO6wGP-EkHBGLxq4KUt6YzFxX_0xiy_6SMJyigV7w"
TOKEN_NOTE="Arbiter phone app — infraction + player endpoints"
TOKEN_SCOPES="infraction,player"

echo "══════════════════════════════════════════════════════════════"
echo "  SouthSeer — Arbiter Integration Setup"
echo "══════════════════════════════════════════════════════════════"
echo ""

# ── Step 1: Run migration ────────────────────────────────────────────────────
echo "▸ Step 1: Running Alembic migration (creates infractions table)..."

if docker compose ps db --status running &> /dev/null 2>&1; then
    echo "  Docker detected — running migration via Docker..."
    docker compose run --rm migrate
else
    echo "  Running migration locally..."
    DB_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/southseer}"
    python3 scripts/upgrade.py "$DB_URL" head
fi

echo "  ✓ Migration complete."
echo ""

# ── Step 2: Insert API token ─────────────────────────────────────────────────
echo "▸ Step 2: Inserting API token for Arbiter..."

# Write the SQL to a temp file to avoid shell escaping issues
SQL_FILE=$(mktemp)
cat > "$SQL_FILE" << 'EOSQL'
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM tokens WHERE key = 'PLACEHOLDER_TOKEN') THEN
        INSERT INTO tokens (key, note, scopes, created_at, updated_at)
        VALUES (
            'PLACEHOLDER_TOKEN',
            'PLACEHOLDER_NOTE',
            'PLACEHOLDER_SCOPES',
            NOW() AT TIME ZONE 'utc',
            NOW() AT TIME ZONE 'utc'
        );
        RAISE NOTICE 'Token inserted.';
    ELSE
        UPDATE tokens
        SET scopes = 'PLACEHOLDER_SCOPES',
            note = 'PLACEHOLDER_NOTE',
            updated_at = NOW() AT TIME ZONE 'utc'
        WHERE key = 'PLACEHOLDER_TOKEN';
        RAISE NOTICE 'Token already existed — updated scopes.';
    END IF;
END
$$;
EOSQL

# Replace placeholders with actual values
sed -i "s|PLACEHOLDER_TOKEN|$API_TOKEN|g" "$SQL_FILE"
sed -i "s|PLACEHOLDER_NOTE|$TOKEN_NOTE|g" "$SQL_FILE"
sed -i "s|PLACEHOLDER_SCOPES|$TOKEN_SCOPES|g" "$SQL_FILE"

if docker compose ps db --status running &> /dev/null 2>&1; then
    docker compose exec -T db psql -U postgres -d southseer < "$SQL_FILE"
    echo "  ✓ Token inserted via Docker."
elif command -v psql &> /dev/null; then
    DB_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/southseer}"
    psql "$DB_URL" < "$SQL_FILE"
    echo "  ✓ Token inserted."
else
    echo "  ✗ Could not connect to database. Run this SQL manually:"
    echo ""
    cat "$SQL_FILE"
    echo ""
fi

rm -f "$SQL_FILE"

echo ""
echo "══════════════════════════════════════════════════════════════"
echo "  ✓ Setup complete!"
echo ""
echo "  Token:  $API_TOKEN"
echo "  Scopes: $TOKEN_SCOPES"
echo ""
echo "  This token is already set in:"
echo "    Arbiter/.env → SEER_API_TOKEN"
echo ""
echo "  Next steps:"
echo "    1. cd seer-main && docker compose up --build -d"
echo "    2. cd arbiter-backend && docker compose up --build -d"
echo "    3. In the Arbiter app Settings, enter your Discord Guild ID"
echo "       (your server ID: right-click server → Copy Server ID)"
echo "══════════════════════════════════════════════════════════════"
