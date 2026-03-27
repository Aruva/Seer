from __future__ import annotations

import factory

from seer.models import Verify


class VerifyFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Verify
        sqlalchemy_session_persistence = "flush"
