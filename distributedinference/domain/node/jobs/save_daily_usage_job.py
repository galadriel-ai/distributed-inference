from dataclasses import dataclass
from typing import Dict
from typing import List
from uuid import UUID

from distributedinference.api_logger import api_logger
from distributedinference.repository.tokens_queue_repository import (
    TokensQueueRepository,
)
from distributedinference.repository.tokens_repository import (
    DailyUserModelUsageIncrement,
)
from distributedinference.repository.tokens_repository import TokensRepository

BATCH_SIZE = 100

logger = api_logger.get()


async def execute(
    tokens_repository: TokensRepository, tokens_queue_repository: TokensQueueRepository
) -> None:
    while True:
        try:
            await _handle_daily_usage_updates(
                tokens_repository, tokens_queue_repository
            )
        except Exception as e:
            logger.error(f"Error updating daily usage: {str(e)}")


async def _handle_daily_usage_updates(
    tokens_repository: TokensRepository, tokens_queue_repository: TokensQueueRepository
) -> None:
    batch = []
    batch.append(await tokens_queue_repository.get_daily_usage_increment())
    # get the rest without blocking
    batch.extend(
        await tokens_queue_repository.fetch_daily_usage_increment_bulk(BATCH_SIZE - 1)
    )
    logger.debug(
        f"save_daily_usage_job.execute() processing {len(batch)} daily usage increments"
    )
    aggregated = _aggregate_usage(batch)
    logger.debug(
        f"save_daily_usage_job.execute() aggregated to {len(aggregated)} daily usage increments"
    )
    await tokens_repository.increment_daily_usage_bulk(aggregated)


@dataclass(frozen=True)
class UserModel:
    user_profile_id: UUID
    model_name: str


@dataclass(frozen=True)
class UsageCount:
    requests: int
    tokens: int


def _aggregate_usage(
    data: List[DailyUserModelUsageIncrement],
) -> List[DailyUserModelUsageIncrement]:
    aggregated: Dict[UserModel, UsageCount] = {}

    for item in data:
        user_model = UserModel(item.user_profile_id, item.model_name)
        usage = aggregated.get(user_model, UsageCount(0, 0))
        aggregated[user_model] = UsageCount(
            requests=usage.requests + item.requests_count,
            tokens=usage.tokens + item.tokens_count,
        )

    return [
        DailyUserModelUsageIncrement(
            user_profile_id=user_model.user_profile_id,
            model_name=user_model.model_name,
            requests_count=usage_count.requests,
            tokens_count=usage_count.tokens,
        )
        for user_model, usage_count in aggregated.items()
    ]
