from dataclasses import dataclass


@dataclass(frozen=True)
class UserSignup:
    password: str
    email: str
