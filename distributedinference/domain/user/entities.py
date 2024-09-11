from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class User:
    uid: UUID
    name: str
    email: str
    authentication_id: str = None


@dataclass(frozen=True)
class UserAuthenticationResponse:
    provider_user_id: str
    session_token: str
