from typing import List
from uuid import UUID

from distributedinference.domain.node.entities import NodeStatus
from distributedinference.domain.node.entities import UserNodeInfo
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.repository.user_node_repository import UserNodeRepository
from distributedinference.service.node.entities import ListNodeRequestNode
from distributedinference.service.node.entities import ListNodeResponse


async def execute(
    user_profile_id: UUID,
    user_node_repository: UserNodeRepository,
    node_repository: NodeRepository,
    tokens_repository: TokensRepository,
) -> ListNodeResponse:
    nodes = await user_node_repository.get_nodes(user_profile_id)
    return await _format(node_repository, tokens_repository, nodes)


async def _format(
    repository: NodeRepository,
    tokens_repository: TokensRepository,
    nodes: List[UserNodeInfo],
) -> ListNodeResponse:
    result = []
    for node in nodes:
        # return metrics only if node is active
        node_metrics = await repository.get_node_metrics(node.node_id)
        current_uptime = 0 if not node_metrics else node_metrics.current_uptime
        status = node_metrics.status if node_metrics else NodeStatus.STOPPED
        result.append(
            ListNodeRequestNode(
                node_id=node.name,
                name_alias=node.name_alias,
                gpu_model=node.specs.gpu_model if node.specs else None,
                vram=node.specs.vram if node.specs else None,
                gpu_count=node.specs.gpu_count if node.specs else None,
                cpu_model=node.specs.cpu_model if node.specs else None,
                cpu_count=node.specs.cpu_count if node.specs else None,
                ram=node.specs.ram if node.specs else None,
                network_download_speed=(
                    node.specs.network_download_speed if node.specs else None
                ),
                network_upload_speed=(
                    node.specs.network_upload_speed if node.specs else None
                ),
                operating_system=node.specs.operating_system if node.specs else None,
                status=status.description(),
                run_duration_seconds=current_uptime,
                total_uptime_seconds=node.uptime or 0,
                requests_served=node.requests_served or 0,
                requests_served_day=await tokens_repository.get_latest_count_by_time_and_node(
                    node.node_id
                ),
                benchmark_tokens_per_second=node.benchmark_tokens_per_second,
                is_archived=node.is_archived,
                node_created_at=(
                    0 if not node.created_at else int(node.created_at.timestamp())
                ),
            )
        )
    return ListNodeResponse(response="OK", nodes=result)
