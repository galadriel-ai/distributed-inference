from typing import List
from unittest.mock import AsyncMock

from uuid_extensions import uuid7

from distributedinference.domain.node.jobs import save_tokens_job as job
from distributedinference.repository.tokens_repository import UsageTokens
from distributedinference.repository.tokens_repository import TokensRepository


class MockRepository:
    def __init__(self, token_usages):
        self.token_usages = token_usages
        self.index = 0

    async def get_token_usage(self):
        token_usage = self.token_usages[self.index]
        self.index += 1
        return token_usage

    async def fetch_token_usage_bulk(self, batch_size: int) -> List[UsageTokens]:
        return self.token_usages[self.index : self.index + batch_size]


async def test_success():
    producer_id = uuid7()
    consumer_id = uuid7()
    test_usage = [
        UsageTokens(
            producer_node_info_id=producer_id,
            consumer_user_profile_id=consumer_id,
            model_name="model-1",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        ),
        UsageTokens(
            producer_node_info_id=consumer_id,
            consumer_user_profile_id=producer_id,
            model_name="model-2",
            prompt_tokens=120,
            completion_tokens=80,
            total_tokens=200,
        ),
    ]
    tokens_queue_repository = MockRepository(test_usage)

    token_repository = AsyncMock(spec=TokensRepository)

    await job._handle_token_usage_updates(token_repository, tokens_queue_repository)
    token_repository.insert_usage_tokens_bulk.assert_called_once_with(test_usage)
