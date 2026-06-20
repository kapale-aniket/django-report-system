from dataclasses import dataclass

from domain.accounts.entities import UserProfile


@dataclass(frozen=True)
class CreateUserResult:
    profile: UserProfile
    password: str
    email_sent: bool
    email_notice: str | None = None
