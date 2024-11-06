from typing import List

from prometheus_client import Gauge

from distributedinference.repository.metrics_repository import MetricsRepository
from distributedinference.repository.metrics_repository import NodeStatusesByModel

node_status_gauge = Gauge(
    "node_status",
    "Node status counts by model name and status",
    ["status", "model_name"],
)


async def execute(metrics_repository: MetricsRepository):
    node_status_gauge.clear()
    statuses: List[NodeStatusesByModel] = await metrics_repository.get_node_statuses()
    for status in statuses:
        node_status_gauge.labels(status.status, status.model_name).set(status.count)
