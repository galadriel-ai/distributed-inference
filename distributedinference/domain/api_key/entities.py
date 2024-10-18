from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class CreatedApiKey:
    api_key_id: UUID
    api_key: str
    created_at: str
