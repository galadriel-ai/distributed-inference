from distributedinference import api_logger
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
            await _handle_token_usage_updates(
                tokens_repository, tokens_queue_repository
            )
        except Exception as e:
            logger.error(f"Error inserting usage tokens: {str(e)}")


async def _handle_token_usage_updates(
    tokens_repository: TokensRepository, tokens_queue_repository: TokensQueueRepository
) -> None:
    # get one with blocking
    batch = []
    batch.append(await tokens_queue_repository.get_token_usage())
    # get the rest without blocking
    batch.extend(await tokens_queue_repository.fetch_token_usage_bulk(BATCH_SIZE - 1))
    logger.debug(f"save_tokens_job.execute() processing {len(batch)} usage information")
    await tokens_repository.insert_usage_tokens_bulk(batch)
