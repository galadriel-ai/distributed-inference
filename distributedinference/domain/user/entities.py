from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class User:
    uid: UUID
    name: str
    email: str
    username: str = None
    profile_data: dict = None
    authentication_id: str = None


@dataclass(frozen=True)
class ApiKey:
    api_key: str
    created_at: datetime


@dataclass(frozen=True)
class UserAuthenticationResponse:
    provider_user_id: str
    session_token: str
