from typing import List
from uuid import UUID

from distributedinference.domain.node.entities import NodeInfo
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.node.entities import ListNodeRequestNode
from distributedinference.service.node.entities import ListNodeResponse


async def execute(
    user_profile_id: UUID, repository: NodeRepository
) -> ListNodeResponse:
    nodes = await repository.get_user_nodes(user_profile_id)
    return _format(nodes)


def _format(nodes: List[NodeInfo]) -> ListNodeResponse:
    result = []
    for node in nodes:
        result.append(ListNodeRequestNode(node_id=str(node.node_id)))
    return ListNodeResponse(response="OK", nodes=result)
