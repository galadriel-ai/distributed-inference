from dataclasses import dataclass
from datetime import date
from datetime import datetime
from typing import List
from typing import Optional
from uuid import UUID

import sqlalchemy
from uuid_extensions import uuid7

from distributedinference import api_logger
from distributedinference.repository.connection import SessionProvider
from distributedinference.repository.utils import historic_uuid
from distributedinference.repository.utils import historic_uuid_seconds
from distributedinference.repository.utils import utcnow, utctoday
from distributedinference.utils.timer import async_timer

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

SQL_GET_NODE_LATEST_USAGE_TOKENS = """
SELECT
    consumer_user_profile_id,
    producer_node_info_id,
    model_name,
    prompt_tokens,
    completion_tokens,
    total_tokens,
    created_at
FROM usage_tokens
WHERE producer_node_info_id = :producer_node_info_id
ORDER BY id DESC LIMIT :count;
"""

SQL_GET_COUNT_BY_TIME = """
SELECT
    count(*) AS usage_count
FROM
    usage_tokens
WHERE
    id > :start_id;
"""

SQL_GET_COUNT_BY_TIME_AND_NODE = """
SELECT 
    count(*) AS usage_count
FROM 
    usage_tokens 
WHERE 
    producer_node_info_id = :producer_node_info_id
    AND id > :start_id;
"""

SQL_GET_COUNT_BY_TIME_AND_USER = """
SELECT
    count(*) AS usage_count
FROM
    usage_tokens ut
LEFT JOIN node_info ni on ut.producer_node_info_id = ni.id
WHERE
    ni.user_profile_id = :user_profile_id
    AND ut.id > :start_id;
"""

SQL_GET_COUNT_AND_OLDEST_USAGE_BY_TIME_AND_CONSUMER_USER_PROFILE_ID = """
SELECT
    count(*) AS requests_count,
    MIN(id::text) AS id,
    MIN(created_at) AS created_at
FROM
    usage_tokens ut
WHERE
    ut.consumer_user_profile_id = :consumer_user_profile_id
    AND model_name = :model
    AND ut.id > :start_id;
"""

SQL_GET_TOKENS_COUNT_AND_OLDEST_USAGE_BY_TIME_AND_CONSUMER_USER_PROFILE_ID = """
SELECT
    SUM(total_tokens) AS tokens_count,
    MIN(id::text) AS id,
    MIN(created_at) AS created_at
FROM
    usage_tokens ut
WHERE
    ut.consumer_user_profile_id = :consumer_user_profile_id
    AND model_name = :model
    AND ut.id > :start_id;
"""

SQL_GET_USER_GROUPED_USAGES_BY_MODEL = """
SELECT
    model_name,
    SUM(total_tokens) AS tokens_count,
    MAX(created_at) AS max_created_at
FROM
    usage_tokens
WHERE
    consumer_user_profile_id = :consumer_user_profile_id
    AND created_at > :start_time
GROUP BY model_name;
"""

SQL_GET_USER_MODEL_DAILY_USAGE = """
SELECT
    model_name,
    tokens_consumed,
    requests_count,
    usage_date
FROM
    user_model_usage_24h
WHERE
    user_profile_id = :user_profile_id
    AND model_name = :model_name
    AND usage_date = CURRENT_DATE;
"""

SQL_INCREMENT_USER_MODEL_DAILY_USAGE = """
INSERT INTO user_model_usage_24h (
    user_profile_id,
    model_name,
    usage_date,
    tokens_consumed,
    requests_count,
    created_at,
    last_updated_at
)
VALUES (
    :user_profile_id,
    :model_name,
    :usage_date,
    :tokens_to_add,
    :requests_to_add,
    :created_at,
    :last_updated_at
)
ON CONFLICT (user_profile_id, model_name, usage_date)
DO UPDATE SET
    tokens_consumed = user_model_usage_24h.tokens_consumed + EXCLUDED.tokens_consumed,
    requests_count = user_model_usage_24h.requests_count + EXCLUDED.requests_count,
    last_updated_at = NOW();
"""

logger = api_logger.get()


@dataclass
class UsageTokens:
    consumer_user_profile_id: UUID
    producer_node_info_id: UUID
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class TimedUsageTokens(UsageTokens):
    created_at: datetime


@dataclass
class UsageNodeModelTotalTokens:
    model_name: str
    node_uid: UUID
    total_tokens: int


@dataclass
class TotalTokensResponse:
    usage: List[UsageNodeModelTotalTokens]
    last_id: Optional[UUID]


@dataclass
class UsageInformation:
    count: int
    oldest_usage_id: UUID
    oldest_usage_created_at: datetime


@dataclass
class DailyUserModelUsage:
    model_name: str
    total_requests_count: int
    total_tokens_count: int
    date: date


@dataclass
class DailyUserModelUsageIncrement:
    user_profile_id: UUID
    model_name: str
    requests_count: int
    tokens_count: int


@dataclass
class ModelUsageInformation:
    model_name: str
    tokens_count: int
    max_created_at: datetime


class TokensRepository:

    def __init__(
        self, session_provider: SessionProvider, session_provider_read: SessionProvider
    ):
        self._session_provider = session_provider
        self._session_provider_read = session_provider_read

    @async_timer("tokens_repository.insert_usage_tokens", logger=logger)
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
            logger.debug("tokens_repository.insert_usage_tokens execute()")
            await session.execute(sqlalchemy.text(SQL_INSERT_USAGE_TOKENS), data)
            logger.debug("tokens_repository.insert_usage_tokens commit()")
            await session.commit()
            logger.debug("tokens_repository.insert_usage_tokens done()")

    @async_timer("tokens_repository.insert_usage_tokens_bulk", logger=logger)
    async def insert_usage_tokens_bulk(self, uts: List[UsageTokens]):
        data = [
            {
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
            for ut in uts
        ]
        logger.debug(
            f"tokens_repository.insert_usage_tokens_bulk inserting {len(data)} rows"
        )
        async with self._session_provider.get() as session:
            logger.debug("tokens_repository.insert_usage_tokens_bulk execute()")
            await session.execute(sqlalchemy.text(SQL_INSERT_USAGE_TOKENS), data)
            logger.debug("tokens_repository.insert_usage_tokens_bulk commit()")
            await session.commit()
            logger.debug("tokens_repository.insert_usage_tokens_bulk done()")

    # pylint: disable=W0613
    @async_timer("tokens_repository.get_node_latest_usage_tokens", logger=logger)
    async def get_node_latest_usage_tokens(
        self, node_id: UUID, count: int
    ) -> List[TimedUsageTokens]:
        data = {"producer_node_info_id": node_id, "count": count}
        tokens = []
        async with self._session_provider_read.get() as session:
            rows = await session.execute(
                sqlalchemy.text(SQL_GET_NODE_LATEST_USAGE_TOKENS), data
            )
            for row in rows:
                tokens.append(
                    TimedUsageTokens(
                        consumer_user_profile_id=row.consumer_user_profile_id,
                        producer_node_info_id=row.producer_node_info_id,
                        model_name=row.model_name,
                        prompt_tokens=row.prompt_tokens,
                        completion_tokens=row.completion_tokens,
                        total_tokens=row.total_tokens,
                        created_at=row.created_at,
                    )
                )
        return tokens

    @async_timer("tokens_repository.get_latest_count_by_time", logger=logger)
    async def get_latest_count_by_time(self, hours: int = 24) -> int:
        data = {"start_id": historic_uuid(hours)}
        async with self._session_provider_read.get() as session:
            rows = await session.execute(sqlalchemy.text(SQL_GET_COUNT_BY_TIME), data)
            for row in rows:
                return row.usage_count
        return 0

    @async_timer("tokens_repository.get_latest_count_by_time_and_node", logger=logger)
    async def get_latest_count_by_time_and_node(
        self, node_id: UUID, hours: int = 24
    ) -> int:
        data = {"producer_node_info_id": node_id, "start_id": historic_uuid(hours)}
        async with self._session_provider_read.get() as session:
            rows = await session.execute(
                sqlalchemy.text(SQL_GET_COUNT_BY_TIME_AND_NODE), data
            )
            for row in rows:
                return row.usage_count
        return 0

    @async_timer("tokens_repository.get_latest_count_by_time_and_user", logger=logger)
    async def get_latest_count_by_time_and_user(
        self, user_id: UUID, hours: int = 24
    ) -> int:
        data = {"user_profile_id": user_id, "start_id": historic_uuid(hours)}
        async with self._session_provider_read.get() as session:
            rows = await session.execute(
                sqlalchemy.text(SQL_GET_COUNT_BY_TIME_AND_USER), data
            )
            for row in rows:
                return row.usage_count
        return 0

    @async_timer(
        "tokens_repository.get_requests_usage_by_time_and_consumer", logger=logger
    )
    async def get_requests_usage_by_time_and_consumer(
        self, consumer_user_profile_id: UUID, model: str, seconds: int = 60
    ) -> UsageInformation:
        data = {
            "consumer_user_profile_id": consumer_user_profile_id,
            "start_id": historic_uuid_seconds(seconds),
            "model": model,
        }
        async with self._session_provider_read.get() as session:
            result = await session.execute(
                sqlalchemy.text(
                    SQL_GET_COUNT_AND_OLDEST_USAGE_BY_TIME_AND_CONSUMER_USER_PROFILE_ID
                ),
                data,
            )
            row = result.first()
            if row:
                return UsageInformation(
                    count=row.requests_count,
                    oldest_usage_id=row.id,
                    oldest_usage_created_at=row.created_at,
                )
        return UsageInformation(
            count=0, oldest_usage_id=uuid7(), oldest_usage_created_at=utcnow()
        )

    @async_timer(
        "tokens_repository.get_tokens_usage_by_time_and_consumer", logger=logger
    )
    async def get_tokens_usage_by_time_and_consumer(
        self,
        consumer_user_profile_id: UUID,
        model: str,
        seconds: int = 60,
    ) -> UsageInformation:
        data = {
            "consumer_user_profile_id": consumer_user_profile_id,
            "model": model,
            "start_id": historic_uuid_seconds(seconds),
        }
        async with self._session_provider_read.get() as session:
            result = await session.execute(
                sqlalchemy.text(
                    SQL_GET_TOKENS_COUNT_AND_OLDEST_USAGE_BY_TIME_AND_CONSUMER_USER_PROFILE_ID
                ),
                data,
            )
            row = result.first()
            if row:
                return UsageInformation(
                    count=row.tokens_count or 0,
                    oldest_usage_id=row.id or uuid7(),
                    oldest_usage_created_at=row.created_at or utcnow(),
                )
        return UsageInformation(
            count=0, oldest_usage_id=uuid7(), oldest_usage_created_at=utcnow()
        )

    @async_timer("tokens_repository.get_grouped_usages_by_time", logger=logger)
    async def get_grouped_usages_by_time(
        self, consumer_user_profile_id: UUID, start_time: datetime
    ) -> List[ModelUsageInformation]:
        data = {
            "consumer_user_profile_id": consumer_user_profile_id,
            "start_time": start_time,
        }
        results = []
        async with self._session_provider_read.get() as session:
            rows = await session.execute(
                sqlalchemy.text(SQL_GET_USER_GROUPED_USAGES_BY_MODEL),
                data,
            )
            for row in rows:
                results.append(
                    ModelUsageInformation(
                        model_name=row.model_name,
                        tokens_count=row.tokens_count,
                        max_created_at=row.max_created_at,
                    )
                )
        return results

    @async_timer("tokens_repository.get_daily_usage", logger=logger)
    async def get_daily_usage(
        self, user_profile_id: UUID, model: str
    ) -> DailyUserModelUsage:
        data = {"user_profile_id": user_profile_id, "model_name": model}
        async with self._session_provider_read.get() as session:
            result = await session.execute(
                sqlalchemy.text(SQL_GET_USER_MODEL_DAILY_USAGE),
                data,
            )
            row = result.first()
            return DailyUserModelUsage(
                model_name=row.model_name if row else model,
                total_tokens_count=row.tokens_consumed if row else 0,
                total_requests_count=row.requests_count if row else 0,
                date=row.usage_date if row else utctoday(),
            )

    @async_timer("tokens_repository.increment_daily_usage", logger=logger)
    async def increment_daily_usage(
        self,
        daily_usage_inc: DailyUserModelUsageIncrement,
    ) -> None:
        data = {
            "user_profile_id": daily_usage_inc.user_profile_id,
            "model_name": daily_usage_inc.model_name,
            "tokens_to_add": daily_usage_inc.tokens_count,
            "requests_to_add": daily_usage_inc.requests_count,
            "usage_date": utctoday(),
            "created_at": utcnow(),
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            logger.debug("tokens_repository.increment_daily_usage execute()")
            await session.execute(
                sqlalchemy.text(SQL_INCREMENT_USER_MODEL_DAILY_USAGE),
                data,
            )
            logger.debug("tokens_repository.increment_daily_usage commit()")
            await session.commit()
            logger.debug("tokens_repository.increment_daily_usage done()")

    @async_timer("tokens_repository.increment_daily_usage_bulk", logger=logger)
    async def increment_daily_usage_bulk(
        self,
        daily_usage_incs: List[DailyUserModelUsageIncrement],
    ) -> None:
        data = [
            {
                "user_profile_id": daily_usage_inc.user_profile_id,
                "model_name": daily_usage_inc.model_name,
                "tokens_to_add": daily_usage_inc.tokens_count,
                "requests_to_add": daily_usage_inc.requests_count,
                "usage_date": utctoday(),
                "created_at": utcnow(),
                "last_updated_at": utcnow(),
            }
            for daily_usage_inc in daily_usage_incs
        ]
        logger.debug(
            f"tokens_repository.increment_daily_usage_bulk inserting {len(data)} rows"
        )
        async with self._session_provider.get() as session:
            logger.debug("tokens_repository.increment_daily_usage_bulk execute()")
            await session.execute(
                sqlalchemy.text(SQL_INCREMENT_USER_MODEL_DAILY_USAGE),
                data,
            )
            logger.debug("tokens_repository.increment_daily_usage_bulk commit()")
            await session.commit()
            logger.debug("tokens_repository.increment_daily_usage_bulk done()")
