from dataclasses import dataclass
from datetime import datetime
from typing import List
from typing import Optional
from uuid import UUID

import sqlalchemy
from uuid_extensions import uuid7

from distributedinference.repository.connection import SessionProvider
from distributedinference.repository.utils import historic_uuid
from distributedinference.repository.utils import utcnow

SQL_INSERT_USAGE_TOKENS = """
INSERT INTO usage_tokens (
    id,
    consumer_user_profile_id,
    producer_node_info_id,
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
    :producer_node_info_id,
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

SQL_GET_TOTAL_TOKENS_BY_NODE_IDS = """
SELECT
    producer_user_profile_id,
    model_name,
    SUM(total_tokens) AS total_tokens
FROM usage_tokens
WHERE producer_user_profile_id = ANY(:node_ids)
GROUP BY producer_user_profile_id, model_name;
"""

SQL_GET_COUNT_BY_TIME = """
SELECT
    count(*) AS usage_count
FROM
    usage_tokens
WHERE
    id > :start_id;
"""

SQL_GET_COUNT_BY_TIME_AND_USER = """
SELECT 
    count(*) AS usage_count
FROM 
    usage_tokens 
WHERE 
    producer_user_profile_id = :producer_user_profile_id
    AND id > :start_id;
"""


@dataclass
class UsageTokens:
    consumer_user_profile_id: UUID
    producer_node_info_id: UUID
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    created_at: Optional[datetime] = None


@dataclass
class UsageNodeModelTotalTokens:
    model_name: str
    node_uid: UUID
    total_tokens: int


class TokensRepository:

    def __init__(self, session_provider: SessionProvider):
        self._session_provider = session_provider

    async def insert_usage_tokens(self, ut: UsageTokens):
        data = {
            "id": uuid7(),
            "consumer_user_profile_id": ut.consumer_user_profile_id,
            "producer_node_info_id": ut.producer_node_info_id,
            "model_name": ut.model_name,
            "prompt_tokens": ut.prompt_tokens,
            "completion_tokens": ut.completion_tokens,
            "total_tokens": ut.total_tokens,
            "created_at": utcnow(),
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_INSERT_USAGE_TOKENS), data)
            await session.commit()

    async def get_user_latest_usage_tokens(
        self, user_id: UUID, node_id: UUID, count: int
    ) -> List[UsageTokens]:
        data = {"node_id": node_id, "user_profile_id": user_id, "count": count}
        tokens = []
        async with self._session_provider.get() as session:
            rows = await session.execute(
                sqlalchemy.text(SQL_GET_USER_LATEST_USAGE_TOKENS), data
            )
            for row in rows:
                tokens.append(
                    UsageTokens(
                        consumer_user_profile_id=row.consumer_user_profile_id,
                        producer_node_info_id=row.producer_user_profile_id,
                        model_name=row.model_name,
                        prompt_tokens=row.prompt_tokens,
                        completion_tokens=row.completion_tokens,
                        total_tokens=row.total_tokens,
                        created_at=row.created_at,
                    )
                )
        return tokens

    async def get_total_tokens_by_node_ids(
        self, node_ids: List[UUID]
    ) -> List[UsageNodeModelTotalTokens]:
        data = {"node_ids": node_ids}
        tokens = []
        async with self._session_provider.get() as session:
            rows = await session.execute(
                sqlalchemy.text(SQL_GET_TOTAL_TOKENS_BY_NODE_IDS), data
            )
            for row in rows:
                tokens.append(
                    UsageNodeModelTotalTokens(
                        node_uid=row.producer_user_profile_id,
                        model_name=row.model_name,
                        total_tokens=row.total_tokens,
                    )
                )
        return tokens

    async def get_latest_count_by_time(self, hours: int = 24) -> int:
        data = {"start_id": historic_uuid(hours)}
        async with self._session_provider.get() as session:
            rows = await session.execute(sqlalchemy.text(SQL_GET_COUNT_BY_TIME), data)
            for row in rows:
                return row.usage_count
        return 0

    async def get_latest_count_by_time_and_user(
        self, user_id: UUID, hours: int = 24
    ) -> int:
        data = {"producer_user_profile_id": user_id, "start_id": historic_uuid(hours)}
        async with self._session_provider.get() as session:
            rows = await session.execute(
                sqlalchemy.text(SQL_GET_COUNT_BY_TIME_AND_USER), data
            )
            for row in rows:
                return row.usage_count
        return 0
