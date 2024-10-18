from typing import List
from uuid import UUID

from distributedinference.domain.node.entities import UserNodeInfo
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.service.node.entities import ListNodeRequestNode
from distributedinference.service.node.entities import ListNodeResponse


async def execute(
    user_profile_id: UUID,
    repository: NodeRepository,
    tokens_repository: TokensRepository,
) -> ListNodeResponse:
    nodes = await repository.get_user_nodes(user_profile_id)
    return await _format(repository, tokens_repository, nodes)


async def _format(
    repository: NodeRepository,
    tokens_repository: TokensRepository,
    nodes: List[UserNodeInfo],
) -> ListNodeResponse:
    result = []
    for node in nodes:
        # return metrics only if node is active
        connected_node_metrics = await repository.get_connected_node_metrics(
            node.node_id
        )
        current_uptime = (
            0 if not connected_node_metrics else connected_node_metrics.current_uptime
        )
        result.append(
            ListNodeRequestNode(
                node_id=node.name,
                name_alias=node.name_alias,
                gpu_model=node.gpu_model,
                vram=node.vram,
                gpu_count=node.gpu_count,
                cpu_model=node.cpu_model,
                cpu_count=node.cpu_count,
                ram=node.ram,
                network_download_speed=node.network_download_speed,
                network_upload_speed=node.network_upload_speed,
                operating_system=node.operating_system,
                status="online" if connected_node_metrics else "offline",
                run_duration_seconds=current_uptime,
                total_uptime_seconds=node.uptime or 0,
                requests_served=node.requests_served or 0,
                requests_served_day=await tokens_repository.get_latest_count_by_time_and_node(
                    node.node_id
                ),
                benchmark_tokens_per_second=node.benchmark_tokens_per_second,
                node_created_at=(
                    0 if not node.created_at else int(node.created_at.timestamp())
                ),
            )
        )
    return ListNodeResponse(response="OK", nodes=result)
