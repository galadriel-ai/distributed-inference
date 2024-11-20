from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

GALADRIEL_DOMAIN = "@galadriel.com"


@dataclass(frozen=True)
class User:
    uid: UUID
    name: str
    email: str
    usage_tier_id: UUID
    username: Optional[str] = None
    profile_data: Optional[dict] = None
    authentication_id: Optional[str] = None
    currently_using_api_key: Optional[str] = None

    def is_self_hosted_nodes_provider(self) -> bool:
        return self.email.endswith(GALADRIEL_DOMAIN)


@dataclass(frozen=True)
class ApiKey:
    uid: UUID
    api_key: str
    created_at: datetime


@dataclass(frozen=True)
class UserAuthenticationResponse:
    provider_user_id: str
    session_token: str
