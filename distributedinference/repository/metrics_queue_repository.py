import asyncio
from typing import Optional

from distributedinference.domain.node.entities import NodeMetricsIncrement


class MetricsQueueRepository:

    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue()

    async def push(self, increment: NodeMetricsIncrement) -> None:
        await self.queue.put(increment)

    # Not async to aggregate the results..
    def get(self) -> Optional[NodeMetricsIncrement]:
        """
        if queue is empty raises `QueueEmpty` exception
        """
        return self.queue.get_nowait()
