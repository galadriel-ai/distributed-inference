from typing import Optional

from distributedinference.domain.user.entities import User
from distributedinference.repository.grafana_api_repository import GrafanaApiRepository
from distributedinference.repository.grafana_api_repository import GraphValue
from distributedinference.repository.grafana_api_repository import get_latest_15min_mark
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service import error_responses
from distributedinference.service.graphs.entities import GetGraphResponse
from distributedinference.service.graphs.entities import GetGraphType

GRAPH_HOURS: int = 24


async def execute(
    graph_type: GetGraphType,
    node_name: Optional[str],
    user: User,
    grafana_repository: GrafanaApiRepository,
    node_repository: NodeRepository,
) -> GetGraphResponse:
    if graph_type == "network":
        graph = await grafana_repository.get_network_inferences(hours=GRAPH_HOURS)
    elif graph_type == "user":
        node_ids = await node_repository.get_user_node_ids(user.uid)
        graph = await grafana_repository.get_node_inferences(
            node_ids, hours=GRAPH_HOURS
        )
    elif graph_type == "node":
        if not node_name:
            raise error_responses.ValidationTypeError("node_name not provided")
        node_id = await node_repository.get_user_node_id_by_name(user.uid, node_name)
        if not node_id:
            raise error_responses.NotFoundAPIError("node with the given name not found")
        graph = await grafana_repository.get_node_inferences(
            [node_id], hours=GRAPH_HOURS
        )
    else:
        raise error_responses.NotFoundAPIError("graph_type not found")
    if not graph:
        return await _get_empty_graph(hours=GRAPH_HOURS)
    return _get_formatted_result(graph)


async def _get_empty_graph(hours: int):
    empty_graph = []
    timestamp = get_latest_15min_mark()
    while len(empty_graph) < hours:
        empty_graph.insert(
            0,
            GraphValue(
                timestamp=timestamp,
                value=0,
            ),
        )
        timestamp = timestamp - (60 * 60)
    return _get_formatted_result(empty_graph)


def _get_formatted_result(graph):
    return GetGraphResponse(
        timestamps=[g.timestamp for g in graph],
        values=[g.value for g in graph],
    )
