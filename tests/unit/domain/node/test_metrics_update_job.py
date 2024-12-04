from unittest.mock import AsyncMock

from uuid_extensions import uuid7

from distributedinference.domain.node.jobs import metrics_update_job as job
from distributedinference.domain.node.entities import NodeMetricsIncrement
from distributedinference.repository.node_repository import NodeRepository


class MockRepository:
    def __init__(self, metrics):
        self.metrics = metrics
        self.index = 0

    def get(self):
        metrics = None
        if self.index < len(self.metrics):
            metrics = self.metrics[self.index]
        self.index += 1
        return metrics


async def test_success_one():
    node_id = uuid7()
    metrics_queue_repository = MockRepository(
        [
            NodeMetricsIncrement(
                node_id=node_id,
                model="model",
                requests_served_incerement=12,
                requests_successful_incerement=11,
                requests_failed_increment=1,
                rtt=100,
            )
        ]
    )

    metrics_queue_repository.get = metrics_queue_repository.get
    node_repository = AsyncMock(spec=NodeRepository)

    await job._handle_metrics_update(metrics_queue_repository, node_repository)
    node_repository.increment_node_metrics.assert_called_once_with(
        NodeMetricsIncrement(
            node_id=node_id,
            model="model",
            requests_served_incerement=12,
            requests_successful_incerement=11,
            requests_failed_increment=1,
            time_to_first_token=None,
            inference_tokens_per_second=None,
            uptime_increment=0,
            rtt=100,
        )
    )


async def test_success_aggregates():
    node_id = uuid7()
    metrics_queue_repository = MockRepository(
        [
            NodeMetricsIncrement(
                node_id=node_id,
                model="model",
                requests_served_incerement=1,
                requests_successful_incerement=1,
                requests_failed_increment=0,
                inference_tokens_per_second=None,
                rtt=11,
            ),
            NodeMetricsIncrement(
                node_id=node_id,
                model="model",
                requests_served_incerement=1,
                requests_successful_incerement=0,
                requests_failed_increment=1,
                inference_tokens_per_second=30.5,
                rtt=10,
            ),
        ]
    )

    metrics_queue_repository.get = metrics_queue_repository.get
    node_repository = AsyncMock(spec=NodeRepository)

    await job._handle_metrics_update(metrics_queue_repository, node_repository)
    node_repository.increment_node_metrics.assert_called_once_with(
        NodeMetricsIncrement(
            node_id=node_id,
            model="model",
            requests_served_incerement=2,
            requests_successful_incerement=1,
            requests_failed_increment=1,
            time_to_first_token=None,
            inference_tokens_per_second=30.5,
            uptime_increment=0,
            rtt=10,  # since 10 is the latest RTT
        )
    )
