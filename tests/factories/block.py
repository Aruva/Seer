from __future__ import annotations

import factory

from seer.models import Block


class BlockFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Block
        sqlalchemy_session_persistence = "flush"
