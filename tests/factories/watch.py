from __future__ import annotations

import factory

from seer.models import Watch


class WatchFactory(factory.alchemy.SQLAlchemyModelFactory):
    note = factory.faker.Faker("sentence")

    class Meta:
        model = Watch
        sqlalchemy_session_persistence = "flush"
