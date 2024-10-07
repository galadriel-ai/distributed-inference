import asyncio
from asyncio import QueueEmpty
from typing import Dict
from typing import List
from uuid import UUID

import settings
from distributedinference import api_logger
from distributedinference.domain.node.entities import NodeMetricsIncrement
from distributedinference.repository.metrics_queue_repository import (
    MetricsQueueRepository,
)
from distributedinference.repository.node_repository import NodeRepository

logger = api_logger.get()


async def execute(
    metrics_queue_repository: MetricsQueueRepository,
    node_repository: NodeRepository,
) -> None:
    timeout = settings.METRICS_JOB_TIMEOUT_BETWEEN_RUNS_SECONDS
    while True:
        try:
            await asyncio.sleep(timeout)
            logger.debug("Running metrics update job!")
            await _handle_metrics_update(metrics_queue_repository, node_repository)
        except Exception:
            logger.error(
                f"Failed to run metrics update job, restarting in {timeout} seconds",
                exc_info=True,
            )


async def _handle_metrics_update(
    metrics_queue_repository: MetricsQueueRepository,
    node_repository: NodeRepository,
) -> None:
    all_metrics: List[NodeMetricsIncrement] = []
    try:
        while metrics := metrics_queue_repository.get():
            all_metrics.append(metrics)
    except QueueEmpty:
        pass
    if all_metrics:
        aggregated_metrics = _get_aggregated_metrics(all_metrics)
        for metrics in aggregated_metrics:
            try:
                await node_repository.increment_node_metrics(metrics)
            except Exception:
                logger.error(
                    f"Error while updating node metrics, node_id={metrics.node_id}",
                    exc_info=True,
                )


def _get_aggregated_metrics(
    all_metrics: List[NodeMetricsIncrement],
) -> List[NodeMetricsIncrement]:
    metrics_map: Dict[UUID, NodeMetricsIncrement] = {}
    for metrics in all_metrics:
        if metrics_map.get(metrics.node_id):
            metrics_map[
                metrics.node_id
            ].requests_served_incerement += metrics.requests_served_incerement
            metrics_map[
                metrics.node_id
            ].requests_successful_incerement += metrics.requests_successful_incerement
            metrics_map[
                metrics.node_id
            ].requests_failed_increment += metrics.requests_failed_increment
            metrics_map[metrics.node_id].uptime_increment += metrics.uptime_increment
            if metrics.time_to_first_token:
                metrics_map[metrics.node_id].time_to_first_token = (
                    metrics.time_to_first_token
                )
            metrics_map[metrics.node_id].rtt = (
                metrics.rtt
            )  # overwrite with the latest RTT
        else:
            metrics_map[metrics.node_id] = metrics
    return [v for _, v in metrics_map.items()]
