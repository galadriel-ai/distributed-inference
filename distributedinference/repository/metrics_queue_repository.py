import asyncio
from typing import Optional

from distributedinference.domain.node.entities import NodeMetricsIncrement


class MetricsQueueRepository:

    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue()

    async def push(self, increment: NodeMetricsIncrement) -> None:
        await self.queue.put(increment)

    async def get(self) -> Optional[NodeMetricsIncrement]:
        return await self.queue.get()

