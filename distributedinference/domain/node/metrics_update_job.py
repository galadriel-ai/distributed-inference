import asyncio

from distributedinference.repository.metrics_queue_repository import MetricsQueueRepository
from distributedinference.repository.node_repository import NodeRepository


async def execute(
    metrics_queue_repository: MetricsQueueRepository,
    node_repository: NodeRepository,
) -> None:
    while True:
        await asyncio.sleep(5)
        # Read metrics from queue, push to DB
        print("process metrics")
        metrics = await metrics_queue_repository.get()
        if metrics:
            await node_repository.increment_node_metrics(metrics)
            print("asd")