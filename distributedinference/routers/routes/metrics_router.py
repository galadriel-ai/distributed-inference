from fastapi import APIRouter
from fastapi.responses import Response
from fastapi import Depends

from prometheus_client import CONTENT_TYPE_LATEST
from prometheus_client import CollectorRegistry
from prometheus_client import generate_latest
from prometheus_client import Gauge

from distributedinference import api_logger
from distributedinference.repository.node_repository import NodeRepository

from distributedinference import dependencies

TAG = "Metrics"
router = APIRouter(prefix="/metrics")
router.tags = [TAG]

logger = api_logger.get()

registry = CollectorRegistry()
network_nodes_gauge = Gauge(
    'network_nodes',
    'Nodes in network by model_name',
    ["model_name"],
    registry=registry)


@router.get("")
async def metrics(
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
):
    # TODO: replace model names
    network_nodes_gauge.labels("llama-3.1-8B").set(node_repository.get_nodes_count())
    metrics_data = generate_latest(registry)
    return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)
