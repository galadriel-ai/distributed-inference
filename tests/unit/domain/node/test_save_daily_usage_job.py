from typing import List
from unittest.mock import AsyncMock

from uuid_extensions import uuid7

from distributedinference.domain.node.jobs import save_daily_usage_job as job
from distributedinference.repository.tokens_repository import (
    DailyUserModelUsageIncrement,
)
from distributedinference.repository.tokens_repository import TokensRepository


class MockRepository:
    def __init__(self, usage_increments):
        self.usage_increments = usage_increments
        self.index = 0

    async def get_daily_usage_increment(self):
        usage_increment = self.usage_increments[self.index]
        self.index += 1
        return usage_increment

    async def fetch_daily_usage_increment_bulk(
        self, batch_size: int
    ) -> List[DailyUserModelUsageIncrement]:
        return self.usage_increments[self.index : self.index + batch_size]


async def test_success():
    user_id = uuid7()
    tokens_queue_repository = MockRepository(
        [
            DailyUserModelUsageIncrement(
                user_profile_id=user_id,
                model_name="model",
                requests_count=1,
                tokens_count=100,
            ),
            DailyUserModelUsageIncrement(
                user_profile_id=user_id,
                model_name="model",
                requests_count=1,
                tokens_count=150,
            ),
        ]
    )

    token_repository = AsyncMock(spec=TokensRepository)

    await job._handle_daily_usage_updates(token_repository, tokens_queue_repository)
    token_repository.increment_daily_usage_bulk.assert_called_once_with(
        [
            DailyUserModelUsageIncrement(
                user_profile_id=user_id,
                model_name="model",
                requests_count=2,
                tokens_count=250,
            ),
        ]
    )
