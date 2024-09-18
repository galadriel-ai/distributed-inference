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
    return _format(repository, nodes)


def _format(repository: NodeRepository, nodes: List[UserNodeInfo]) -> ListNodeResponse:
    result = []
    for node in nodes:
        connected_node = repository.get_connected_node_info(node.node_id)
        current_uptime = 0 if not connected_node else connected_node.current_uptime
        result.append(
            ListNodeRequestNode(
                node_id=node.name,
                name_alias=node.name_alias,
                gpu_model=node.gpu_model,
                vram=node.vram,
                cpu_model=node.cpu_model,
                cpu_count=node.cpu_count,
                ram=node.ram,
                network_download_speed=node.network_download_speed,
                network_upload_speed=node.network_upload_speed,
                operating_system=node.operating_system,
                status="online" if connected_node else "offline",
                run_duration_seconds=(node.uptime or 0) + current_uptime,
                requests_served=node.requests_served or 0,
                node_created_at=int(node.created_at.timestamp()),
            )
        )
    return ListNodeResponse(response="OK", nodes=result)
