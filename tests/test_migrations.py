from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from seer.settings import Settings


class TestMigrations:
    def test_alembic(self, settings: Settings) -> None:
        from seer.models import create_all, reverse_all

        create_all(settings.DATABASE_URL)
        reverse_all(settings.DATABASE_URL)
