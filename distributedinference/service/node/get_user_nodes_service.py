from typing import List
from uuid import UUID

from distributedinference.domain.node.entities import UserNodeInfo
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.node.entities import ListNodeRequestNode
from distributedinference.service.node.entities import ListNodeResponse


async def execute(
    user_profile_id: UUID, repository: NodeRepository
) -> ListNodeResponse:
    nodes = await repository.get_user_nodes(user_profile_id)
    return _format(nodes)


def _format(nodes: List[UserNodeInfo]) -> ListNodeResponse:
    result = []
    for node in nodes:
        result.append(
            ListNodeRequestNode(
                node_id=node.name,
                name_alias=node.name_alias,
                status="online" if node.connected else "offline",
                run_duration_seconds=node.uptime or 0,
                requests_served=node.requests_served or 0,
                gpu_model=node.gpu_model,
            )
        )
    return ListNodeResponse(response="OK", nodes=result)
