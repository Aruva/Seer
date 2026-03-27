from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from seer import __version__
from seer.cogs import AboutCog
from tests.mixins import InteractionMixin

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory

pytestmark = pytest.mark.use_db


@pytest.mark.asyncio
class TestCogAbout(InteractionMixin):
    async def test_about(self, freezer: FrozenDateTimeFactory) -> None:
        freezer.move_to("2021-03-01")

        cog = AboutCog(self.bot)
        await self.run(cog.about)

        self.interaction.response.send_message.assert_called_once()  # type: ignore
        assert self.interaction.response.send_message.call_args_list[0].kwargs[  # type: ignore
            "embed"
        ].to_dict() == {
            "color": self.settings.INFO_EMBED_COLOR,
            "description": (
                "_The Discord bot for competitive leagues and tracking results._\n"
                "\n"
                "Having issues with SouthSeer? Please [report bugs]"
                "(https://github.com/Southsidestudio/Seer/issues)!\n"
                "\n"
                f"[🔗 Add SouthSeer to your Discord!]({self.settings.BOT_INVITE_LINK})\n"
                "\n"
                "SouthSeer is built and maintained by Southside Studio and Hobbies.\n"
                "\n"
                "Visit us at [southsidestudioandhobbies.com]"
                "(https://southsidestudioandhobbies.com)"
            ),
            "fields": [
                {
                    "inline": True,
                    "name": "Version",
                    "value": (f"[{__version__}](https://pypi.org/project/seer/{__version__}/)"),
                },
                {
                    "inline": True,
                    "name": "Maintainer",
                    "value": "[Southside Studio and Hobbies](https://southsidestudioandhobbies.com)",
                },
            ],
            "thumbnail": {"url": self.settings.thumb(None)},
            "title": "SouthSeer",
            "type": "rich",
            "url": "https://southsidestudioandhobbies.com",
            "flags": 0,
        }
