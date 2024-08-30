from uuid import UUID

from distributedinference.domain.node.entities import NodeInfo
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.node.entities import PostNodeInfoRequest
from distributedinference.service.node.entities import PostNodeInfoResponse


async def execute(
    request: PostNodeInfoRequest, node_id: UUID, repository: NodeRepository
) -> PostNodeInfoResponse:
    node_info = _request_to_node_info(request)
    await repository.save_node_info(node_id, node_info)
    return PostNodeInfoResponse()


def _request_to_node_info(request: PostNodeInfoRequest) -> NodeInfo:
    return NodeInfo(
        gpu_model=request.gpu_model,
        vram=request.vram,
        cpu_model=request.cpu_model,
        cpu_count=request.cpu_count,
        ram=request.ram,
        network_download_speed=request.network_download_speed,
        network_upload_speed=request.network_upload_speed,
        operating_system=request.operating_system,
    )
