from dataclasses import dataclass
from datetime import datetime
from typing import List
from typing import Optional
from uuid import UUID

import sqlalchemy

from distributedinference import api_logger
from distributedinference.domain.rate_limit.entities import UsageTier
from distributedinference.repository.connection import SessionProvider
from distributedinference.utils.timer import async_timer

SQL_GET_USAGE_TIERS = """
SELECT
    id,
    name,
    description,
    max_tokens_per_minute,
    max_tokens_per_day,
    max_requests_per_minute,
    max_requests_per_day
    created_at,
    last_updated_at
FROM usage_tier;
"""

SQL_GET_USAGE_TIER_BY_ID = """
SELECT
    id,
    name,
    description,
    max_tokens_per_minute,
    max_tokens_per_day,
    max_requests_per_minute,
    max_requests_per_day,
    created_at,
    last_updated_at
FROM usage_tier
WHERE id = :id;
"""

logger = api_logger.get()


class RateLimitRepository:

    def __init__(
        self, session_provider: SessionProvider, session_provider_read: SessionProvider
    ):
        self._session_provider = session_provider
        self._session_provider_read = session_provider_read

    @async_timer("rate_limit_repository.get_usage_tiers", logger=logger)
    async def get_usage_tiers(self) -> List[UsageTier]:
        async with self._session_provider_read.get() as session:
            tiers = []
            rows = await session.execute(sqlalchemy.text(SQL_GET_USAGE_TIERS))
            for row in rows:
                tiers.append(
                    UsageTier(
                        id=row.id,
                        name=row.name,
                        description=row.description,
                        max_tokens_per_minute=row.max_tokens_per_minute,
                        max_tokens_per_day=row.max_tokens_per_day,
                        max_requests_per_minute=row.max_requests_per_minute,
                        max_requests_per_day=row.max_requests_per_day,
                        created_at=row.created_at,
                        last_updated_at=row.last_updated_at,
                    )
                )
            return tiers

    @async_timer("rate_limit_repository.get_usage_tier", logger=logger)
    async def get_usage_tier(self, tier_id: UUID) -> Optional[UsageTier]:
        data = {"id": tier_id}
        async with self._session_provider_read.get() as session:
            result = await session.execute(
                sqlalchemy.text(SQL_GET_USAGE_TIER_BY_ID), data
            )
            row = result.first()
            if row:
                return UsageTier(
                    id=row.id,
                    name=row.name,
                    description=row.description,
                    max_tokens_per_minute=row.max_tokens_per_minute,
                    max_tokens_per_day=row.max_tokens_per_day,
                    max_requests_per_minute=row.max_requests_per_minute,
                    max_requests_per_day=row.max_requests_per_day,
                    created_at=row.created_at,
                    last_updated_at=row.last_updated_at,
                )
            return None
