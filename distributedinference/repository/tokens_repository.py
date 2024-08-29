import asyncio
from dataclasses import dataclass
from uuid import UUID

from uuid_extensions import uuid7

from distributedinference.repository import connection
from distributedinference.repository.utils import utcnow

SQL_INSERT_USAGE_TOKENS = """
INSERT INTO usage_tokens (
    id,
    consumer_user_profile_id,
    producer_user_profile_id,
    model_name,
    prompt_tokens,
    completion_tokens,
    total_tokens,
    created_at,
    last_updated_at
)
VALUES (
    :id,
    :consumer_user_profile_id,
    :producer_user_profile_id,
    :model_name,
    :prompt_tokens,
    :completion_tokens,
    :total_tokens,
    :created_at,
    :last_updated_at
);
"""


@dataclass
class UsageTokens:
    consumer_user_profile_id: UUID
    producer_user_profile_id: UUID
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class TokensRepository:

    async def insert_usage_tokens(self, ut: UsageTokens):
        data = {
            "id": uuid7(),
            "consumer_user_profile_id": ut.consumer_user_profile_id,
            "producer_user_profile_id": ut.producer_user_profile_id,
            "model_name": ut.model_name,
            "prompt_tokens": ut.prompt_tokens,
            "completion_tokens": ut.completion_tokens,
            "total_tokens": ut.total_tokens,
            "created_at": utcnow(),
            "last_updated_at": utcnow(),
        }
        await connection.write(SQL_INSERT_USAGE_TOKENS, data)
