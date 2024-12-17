import asyncio
from typing import List

from distributedinference.api_logger import api_logger
from distributedinference.repository.tokens_repository import UsageTokens
from distributedinference.repository.tokens_repository import (
    DailyUserModelUsageIncrement,
)

logger = api_logger.get()


class TokensQueueRepository:

    def __init__(self) -> None:
        self.token_usage_queue: asyncio.Queue = asyncio.Queue()
        self.daily_usage_queue: asyncio.Queue = asyncio.Queue()

    async def push_token_usage(self, usage: UsageTokens) -> None:
        await self.token_usage_queue.put(usage)

    async def get_token_usage(self) -> UsageTokens:
        logger.debug(f"token_usage_queue size: {self.token_usage_queue.qsize()}")
        return await self.token_usage_queue.get()

    async def fetch_token_usage_bulk(self, batch_size: int) -> List[UsageTokens]:
        batch = []
        for _ in range(batch_size - 1):
            try:
                item = self.token_usage_queue.get_nowait()
                batch.append(item)
            except asyncio.QueueEmpty:
                break

        return batch

    async def push_daily_usage(self, usage: DailyUserModelUsageIncrement) -> None:
        await self.daily_usage_queue.put(usage)

    async def get_daily_usage_increment(self) -> DailyUserModelUsageIncrement:
        logger.debug(f"daily_usage_queue size: {self.daily_usage_queue.qsize()}")
        return await self.daily_usage_queue.get()

    async def fetch_daily_usage_increment_bulk(
        self, batch_size: int
    ) -> List[DailyUserModelUsageIncrement]:
        batch = []
        for _ in range(batch_size - 1):
            try:
                item = self.daily_usage_queue.get_nowait()
                batch.append(item)
            except asyncio.QueueEmpty:
                break

        return batch
