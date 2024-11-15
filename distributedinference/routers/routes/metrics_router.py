from typing import List

from fastapi import APIRouter
from fastapi import Depends
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST
from prometheus_client import CollectorRegistry
from prometheus_client import Gauge
from prometheus_client import REGISTRY
from prometheus_client import generate_latest
from prometheus_client.multiprocess import MultiProcessCollector

import settings
from distributedinference import api_logger
from distributedinference import dependencies
from distributedinference.domain.metrics import calculate_node_costs
from distributedinference.domain.metrics import node_status_metrics
from distributedinference.domain.metrics import sql_engine_metrics
from distributedinference.domain.node.entities import NodeBenchmark
from distributedinference.repository.metrics_repository import MetricsRepository
from distributedinference.repository.node_repository import NodeRepository

TAG = "Metrics"
router = APIRouter(prefix="/metrics")
router.tags = [TAG]

logger = api_logger.get()

network_nodes_gauge = Gauge(
    "network_nodes", "Nodes in network by model_name", ["model_name"]
)

locally_connected_nodes_gauge = Gauge(
    "locally_connected_nodes",
    "Connected nodes to the current backend counts by model name, status and node uid",
    ["model_name", "node_uid", "node_status"],
)

node_tokens_gauge = Gauge(
    "node_tokens",
    "Total tokens by model_name and node uid",
    ["model_name", "node_uid"],
)

node_requests_gauge = Gauge(
    "node_requests",
    "Requests by model and node uid",
    ["model_name", "node_uid"],
)
node_requests_successful_gauge = Gauge(
    "node_requests_successful",
    "Successful requests by model and node uid",
    ["model_name", "node_uid"],
)
node_requests_failed_gauge = Gauge(
    "node_requests_failed",
    "Failed requests by model and node uid",
    ["model_name", "node_uid"],
)
node_time_to_first_token_gauge = Gauge(
    "node_time_to_first_token",
    "Time to first token in seconds by model and node uid",
    ["model_name", "node_uid"],
)
node_inference_tokens_per_second_gauge = Gauge(
    "node_inference_tokens_per_second",
    "Real-time tokens per second for each inference call by model and node uid",
    ["model_name", "node_uid"],
)
node_rtt_gauge = Gauge(
    "node_rtt",
    "Round Trip Time for the node",
    ["node_uid"],
)
node_costs_gauge = Gauge(
    "node_costs", "Node GPU 1h rent costs per model", ["model_name"]
)


@router.get("", include_in_schema=False)
async def get_metrics(
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    metrics_repository: MetricsRepository = Depends(
        dependencies.get_metrics_repository
    ),
):
    registry = _get_registry()
    _clear()

    nodes = await metrics_repository.get_connected_node_benchmarks()
    for node in nodes:
        network_nodes_gauge.labels(node.model_name).inc()

    locally_connected_nodes = node_repository.get_locally_connected_nodes()
    for node in locally_connected_nodes:
        locally_connected_nodes_gauge.labels(
            node.model, node.uid, node.node_status
        ).inc()

    node_metrics = await node_repository.get_all_node_metrics()

    for node_uid, metrics in node_metrics.items():
        node_requests_gauge.labels(metrics.model_name, node_uid).set(
            metrics.requests_served
        )
        node_requests_successful_gauge.labels(metrics.model_name, node_uid).set(
            metrics.requests_successful
        )
        node_requests_failed_gauge.labels(metrics.model_name, node_uid).set(
            metrics.requests_failed
        )
        if metrics.time_to_first_token:
            node_time_to_first_token_gauge.labels(metrics.model_name, node_uid).set(
                metrics.time_to_first_token
            )
        if metrics.inference_tokens_per_second:
            node_inference_tokens_per_second_gauge.labels(
                metrics.model_name, node_uid
            ).set(metrics.inference_tokens_per_second)
        if metrics.rtt:
            node_rtt_gauge.labels(node_uid).set(metrics.rtt)

    await _set_node_tokens(metrics_repository)
    await _set_node_costs(nodes)
    await sql_engine_metrics.execute()
    await node_status_metrics.execute(metrics_repository)
    metrics_data = generate_latest(registry)
    return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)


def _get_registry() -> CollectorRegistry:
    if settings.PROMETHEUS_MULTIPROC_DIR:
        registry = CollectorRegistry()
        MultiProcessCollector(registry)
    else:
        registry = REGISTRY
    return registry


def _clear():
    network_nodes_gauge.clear()
    locally_connected_nodes_gauge.clear()
    node_tokens_gauge.clear()
    node_requests_gauge.clear()
    node_requests_successful_gauge.clear()
    node_requests_failed_gauge.clear()
    node_time_to_first_token_gauge.clear()
    node_inference_tokens_per_second_gauge.clear()
    node_rtt_gauge.clear()
    node_costs_gauge.clear()


async def _set_node_tokens(
    metrics_repository: MetricsRepository,
):
    node_usage_total_tokens = await metrics_repository.get_all_nodes_total_tokens()

    for usage in node_usage_total_tokens:
        node_tokens_gauge.labels(usage.model_name, usage.node_uid).set(
            usage.total_tokens
        )


async def _set_node_costs(nodes: List[NodeBenchmark]):
    costs = calculate_node_costs.execute(nodes)
    for model_name, cost in costs.items():
        node_costs_gauge.labels(model_name).set(cost)
