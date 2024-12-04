from collections import defaultdict
from typing import Dict
from typing import List
from typing import Tuple
from uuid import UUID

from distributedinference import api_logger
from distributedinference.repository.tokens_repository import (
    DailyUserModelUsageIncrement,
)
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.repository.tokens_queue_repository import (
    TokensQueueRepository,
)

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


def _aggregate_usage(
    data: List[DailyUserModelUsageIncrement],
) -> List[DailyUserModelUsageIncrement]:
    aggregated: Dict[Tuple[UUID, str], Dict[str, int]] = defaultdict(
        lambda: {"requests_count": 0, "tokens_count": 0}
    )

    for item in data:
        key = (item.user_profile_id, item.model_name)
        aggregated[key]["requests_count"] += item.requests_count
        aggregated[key]["tokens_count"] += item.tokens_count

    return [
        DailyUserModelUsageIncrement(
            user_profile_id=key[0],
            model_name=key[1],
            requests_count=value["requests_count"],
            tokens_count=value["tokens_count"],
        )
        for key, value in aggregated.items()
    ]
