from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from seer.utils import handle_view_errors

if TYPE_CHECKING:
    from seer import Seer


class BaseView(discord.ui.View):
    def __init__(self, bot: Seer) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.on_error = handle_view_errors
