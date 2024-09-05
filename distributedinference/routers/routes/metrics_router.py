import settings
from fastapi import APIRouter
from fastapi.responses import Response
from fastapi import Depends

from prometheus_client import REGISTRY
from prometheus_client import CONTENT_TYPE_LATEST
from prometheus_client import CollectorRegistry
from prometheus_client import generate_latest
from prometheus_client import Gauge
from prometheus_client.multiprocess import MultiProcessCollector

from distributedinference import api_logger
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.tokens_repository import TokensRepository

from distributedinference import dependencies

TAG = "Metrics"
router = APIRouter(prefix="/metrics")
router.tags = [TAG]

logger = api_logger.get()

network_nodes_gauge = Gauge(
    "network_nodes", "Nodes in network by model_name", ["model_name"]
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


@router.get("", include_in_schema=False)
async def metrics(
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    tokens_repository: TokensRepository = Depends(dependencies.get_tokens_repository),
):
    if settings.PROMETHEUS_MULTIPROC_DIR:
        registry = CollectorRegistry()
        MultiProcessCollector(registry)
    else:
        registry = REGISTRY

    network_nodes_gauge.clear()
    nodes = node_repository.get_connected_nodes()
    node_model_names = {node.uid: node.model for node in nodes}
    for node in nodes:
        network_nodes_gauge.labels(node.model).inc()
    connected_node_ids = node_repository.get_connected_node_ids()
    node_metrics = await node_repository.get_node_metrics_by_ids(connected_node_ids)
    node_usage_total_tokens = await tokens_repository.get_total_tokens_by_node_ids(
        connected_node_ids
    )
    node_tokens_gauge.clear()
    node_requests_gauge.clear()
    node_requests_successful_gauge.clear()
    node_requests_failed_gauge.clear()
    node_time_to_first_token_gauge.clear()

    for node_uid, metrics in node_metrics.items():
        node_requests_gauge.labels(node_model_names[node_uid], node_uid).set(
            metrics.requests_served
        )
        node_requests_successful_gauge.labels(node_model_names[node_uid], node_uid).set(
            metrics.requests_successful
        )
        node_requests_failed_gauge.labels(node_model_names[node_uid], node_uid).set(
            metrics.requests_failed
        )
        if metrics.time_to_first_token:
            node_time_to_first_token_gauge.labels(
                node_model_names[node_uid], node_uid
            ).set(metrics.time_to_first_token)

    for usage in node_usage_total_tokens:
        node_tokens_gauge.labels(usage.model_name, usage.node_uid).set(
            usage.total_tokens
        )
    metrics_data = generate_latest(registry)
    return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)
