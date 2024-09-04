from dataclasses import dataclass
from datetime import datetime
from typing import List
from typing import Optional
from uuid import UUID

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession
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

SQL_GET_USER_LATEST_USAGE_TOKENS = """
SELECT
    consumer_user_profile_id,
    producer_user_profile_id,
    model_name,
    prompt_tokens,
    completion_tokens,
    total_tokens,
    created_at
FROM usage_tokens
WHERE producer_user_profile_id = :user_profile_id
ORDER BY id DESC LIMIT :count;
"""


@dataclass
class UsageTokens:
    consumer_user_profile_id: UUID
    producer_user_profile_id: UUID
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    created_at: Optional[datetime] = None


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

    @connection.read_session
    async def get_user_latest_usage_tokens(
        self, node_id: UUID, count: int, session: AsyncSession
    ) -> List[UsageTokens]:
        data = {"user_profile_id": node_id, "count": count}
        rows = await session.execute(
            sqlalchemy.text(SQL_GET_USER_LATEST_USAGE_TOKENS), data
        )
        tokens = []
        for row in rows:
            tokens.append(
                UsageTokens(
                    consumer_user_profile_id=row.consumer_user_profile_id,
                    producer_user_profile_id=row.producer_user_profile_id,
                    model_name=row.model_name,
                    prompt_tokens=row.prompt_tokens,
                    completion_tokens=row.completion_tokens,
                    total_tokens=row.total_tokens,
                    created_at=row.created_at,
                )
            )
        return tokens
