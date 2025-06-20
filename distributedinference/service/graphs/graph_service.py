from typing import Optional

from distributedinference.domain.user.entities import User
from distributedinference.repository.grafana_api_repository import GrafanaApiRepository
from distributedinference.repository.user_node_repository import UserNodeRepository
from distributedinference.service import error_responses
from distributedinference.service.graphs.entities import GetGraphResponse
from distributedinference.service.graphs.entities import GetGraphType

GRAPH_HOURS: int = 24


async def execute(
    graph_type: GetGraphType,
    node_name: Optional[str],
    user: User,
    grafana_repository: GrafanaApiRepository,
    user_node_repository: UserNodeRepository,
) -> GetGraphResponse:
    if graph_type == "network":
        graph = await grafana_repository.get_network_inferences(hours=GRAPH_HOURS)
    elif graph_type == "user":
        node_ids = await user_node_repository.get_node_ids(user.uid)
        graph = await grafana_repository.get_node_inferences(
            node_ids, hours=GRAPH_HOURS
        )
    elif graph_type == "node":
        if not node_name:
            raise error_responses.ValidationTypeError("node_name not provided")
        node_id = await user_node_repository.get_node_id_by_name(user.uid, node_name)
        if not node_id:
            raise error_responses.NotFoundAPIError("node with the given name not found")
        graph = await grafana_repository.get_node_inferences(
            [node_id], hours=GRAPH_HOURS
        )
    else:
        raise error_responses.NotFoundAPIError("graph_type not found")
    return _get_formatted_result(graph)


def _get_formatted_result(graph):
    return GetGraphResponse(
        timestamps=[g.timestamp for g in graph],
        values=[g.value for g in graph],
    )
