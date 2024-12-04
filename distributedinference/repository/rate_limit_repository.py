from typing import List
from typing import Optional
from uuid import UUID

import sqlalchemy

from distributedinference import api_logger
from distributedinference.domain.rate_limit.entities import UsageLimits
from distributedinference.domain.rate_limit.entities import UsageTier
from distributedinference.repository.connection import SessionProvider
from distributedinference.utils.timer import async_timer

SQL_GET_USAGE_LIMITS_BY_ID_AND_MODEL = """
SELECT
    model_name,
    max_tokens_per_minute,
    max_tokens_per_day,
    max_requests_per_minute,
    max_requests_per_day,
    price_per_million_tokens
FROM usage_limit ul
WHERE
    ul.usage_tier_id = :id
    AND ul.model_name = :model;
"""

SQL_GET_USAGE_TIER_LIMITS = """
SELECT
    model_name,
    max_tokens_per_minute,
    max_tokens_per_day,
    max_requests_per_minute,
    max_requests_per_day,
    price_per_million_tokens
FROM usage_limit
WHERE usage_tier_id = :id;
"""

SQL_GET_USAGE_TIER_INFO = """
SELECT
    name,
    description
FROM usage_tier
WHERE id = :id;
"""

SQL_GET_USER_MODEL_BUCKET = """
SELECT
    model_name,
    requests_remaining_minute,
    tokens_remaining_minute,
    requests_remaining_day,
    tokens_remaining_day,
    last_updated_at
FROM
    rate_limit_buckets
WHERE
    user_profile_id = :user_profile_id
    AND model_name = :model_name;
"""

SQL_UPDATE_RATE_LIMIT_BUCKETS = """
INSERT INTO rate_limit_buckets (
    user_profile_id,
    model_name,
    requests_remaining_minute,
    tokens_remaining_minute,
    requests_remaining_day,
    tokens_remaining_day,
    created_at,
    last_updated_at
)
VALUES (
    :user_profile_id,
    :model_name,
    GREATEST(0, :requests_remaining_minute),
    GREATEST(0, :tokens_remaining_minute),
    GREATEST(0, :requests_remaining_day),
    GREATEST(0, :tokens_remaining_day),
    :created_at,
    :last_updated_at
)
ON CONFLICT (user_profile_id, model_name)
DO UPDATE SET
    requests_remaining_minute = GREATEST(0, rate_limit_buckets.requests_remaining_minute - EXCLUDED.requests_remaining_minute),
    tokens_remaining_minute = GREATEST(0, rate_limit_buckets.tokens_remaining_minute - EXCLUDED.tokens_remaining_minute),
    requests_remaining_day = GREATEST(0, rate_limit_buckets.requests_remaining_day - EXCLUDED.requests_remaining_day),
    tokens_remaining_day = GREATEST(0, rate_limit_buckets.tokens_remaining_day - EXCLUDED.tokens_remaining_day),
    last_updated_at = NOW();
"""

logger = api_logger.get()


class RateLimitRepository:

    def __init__(
        self, session_provider: SessionProvider, session_provider_read: SessionProvider
    ):
        self._session_provider = session_provider
        self._session_provider_read = session_provider_read

    @async_timer("rate_limit_repository.get_usage_limits_for_model", logger=logger)
    async def get_usage_limits_for_model(
        self, tier_id: UUID, model: str
    ) -> Optional[UsageLimits]:
        data = {"id": tier_id, "model": model}
        async with self._session_provider_read.get() as session:
            result = await session.execute(
                sqlalchemy.text(SQL_GET_USAGE_LIMITS_BY_ID_AND_MODEL), data
            )
            row = result.first()
            if row:
                return UsageLimits(
                    model=row.model_name,
                    max_tokens_per_minute=row.max_tokens_per_minute,
                    max_tokens_per_day=row.max_tokens_per_day,
                    max_requests_per_minute=row.max_requests_per_minute,
                    max_requests_per_day=row.max_requests_per_day,
                    price_per_million_tokens=row.price_per_million_tokens,
                )
            return None

    @async_timer("rate_limit_repository.get_usage_tier_limits", logger=logger)
    async def get_usage_tier_limits(self, tier_id: UUID) -> List[UsageLimits]:
        data = {"id": tier_id}
        results = []
        async with self._session_provider_read.get() as session:
            rows = await session.execute(
                sqlalchemy.text(SQL_GET_USAGE_TIER_LIMITS), data
            )
            for row in rows:
                results.append(
                    UsageLimits(
                        model=row.model_name,
                        max_tokens_per_minute=row.max_tokens_per_minute,
                        max_tokens_per_day=row.max_tokens_per_day,
                        max_requests_per_minute=row.max_requests_per_minute,
                        max_requests_per_day=row.max_requests_per_day,
                        price_per_million_tokens=row.price_per_million_tokens,
                    )
                )
            return results

    @async_timer("rate_limit_repository.get_usage_tier_info", logger=logger)
    async def get_usage_tier_info(self, tier_id: UUID) -> Optional[UsageTier]:
        data = {"id": tier_id}
        async with self._session_provider_read.get() as session:
            result = await session.execute(
                sqlalchemy.text(SQL_GET_USAGE_TIER_INFO), data
            )
            row = result.first()
            if row:
                return UsageTier(id=tier_id, name=row.name, description=row.description)
        return None
