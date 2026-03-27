from __future__ import annotations

from discord.app_commands import AppCommandError


class SeerError(AppCommandError): ...


class AdminOnlyError(SeerError):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or "This command is only available to SouthSeer admins.")


class GuildOnlyError(SeerError):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or "This command is only available within a guild.")


class UserBannedError(SeerError):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or "This user has been banned from using SouthSeer.")


class GuildBannedError(SeerError):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or "This guild has been banned from using SouthSeer.")


class UserVerifiedError(SeerError):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or "Verified user message in a unverified only channel.")


class UserUnverifiedError(SeerError):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or "Unverified user message in a verified only channel.")
