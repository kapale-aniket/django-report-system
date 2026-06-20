from dataclasses import dataclass


@dataclass
class LoginDTO:
    username: str
    password: str
    role_hint: str = ''


@dataclass
class RegisterDTO:
    username: str
    email: str
    password: str
    first_name: str
    last_name: str
    department: str = ''


@dataclass
class ChangePasswordDTO:
    old_password: str
    new_password: str


@dataclass
class ProfileUpdateDTO:
    username: str | None = None
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    department: str | None = None
