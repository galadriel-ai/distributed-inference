from uuid import UUID

from distributedinference.domain.node.entities import FullNodeInfo
from distributedinference.domain.node.entities import NodeInfo
from distributedinference.domain.node.entities import NodeSpecs
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.node.entities import PostNodeInfoRequest
from distributedinference.service.node.entities import PostNodeInfoResponse


async def execute(
    request: PostNodeInfoRequest,
    node_info: NodeInfo,
    user_profile_id: UUID,
    repository: NodeRepository,
) -> PostNodeInfoResponse:
    node_info_update = _request_to_node_info(request, node_info)
    await repository.save_node_info(user_profile_id, node_info_update)
    return PostNodeInfoResponse()


def _request_to_node_info(
    request: PostNodeInfoRequest, node_info: NodeInfo
) -> FullNodeInfo:
    return FullNodeInfo(
        node_id=node_info.node_id,
        name=node_info.name,
        name_alias=node_info.name_alias,
        created_at=None,
        specs=NodeSpecs(
            gpu_model=request.gpu_model,
            vram=request.vram,
            gpu_count=request.gpu_count,
            cpu_model=request.cpu_model,
            cpu_count=request.cpu_count,
            ram=request.ram,
            network_download_speed=request.network_download_speed,
            network_upload_speed=request.network_upload_speed,
            operating_system=request.operating_system,
            version=request.version,
        ),
    )
