#!/usr/bin/env python3
"""Run Alembic migrations to a given revision (default: head).

Usage:
    python3 upgrade.py <database_url> [revision]

Accepts postgresql:// or postgres:// URLs and normalises to the
psycopg3 driver (postgresql+psycopg://) automatically, matching
the same logic used in seer/settings.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

import alembic.command
import alembic.config

# Inside the Docker image the source tree is at /seer/src
MIGRATIONS_DIR = Path("/seer/src/seer/migrations")
ALEMBIC_INI = MIGRATIONS_DIR / "alembic.ini"

if len(sys.argv) < 2:
    print("Usage: upgrade.py <database_url> [revision]", file=sys.stderr)
    sys.exit(1)

url = sys.argv[1]
revision = sys.argv[2] if len(sys.argv) > 2 else "head"

# Normalise to psycopg3 driver — same transformation as settings.py
if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql://", 1)
if url.startswith("postgresql://"):
    url = url.replace("postgresql://", "postgresql+psycopg://", 1)

config = alembic.config.Config(str(ALEMBIC_INI))
config.set_main_option("script_location", str(MIGRATIONS_DIR))
config.set_main_option("sqlalchemy.url", url)
alembic.command.upgrade(config, revision)
