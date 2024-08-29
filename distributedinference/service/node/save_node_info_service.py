from uuid import UUID

from distributedinference.domain.node.entities import NodeInfo
from distributedinference.service.node.entities import NodeInfoRequest
from distributedinference.service.node.entities import NodeInfoResponse
from distributedinference.service.error_responses import InternalServerAPIError
from distributedinference.repository.node_repository import NodeRepository


async def execute(
    request: NodeInfoRequest, node_id: UUID, repository: NodeRepository
) -> NodeInfoResponse:
    node_info = _request_to_node_info(request)
    await repository.save_node_info(node_id, node_info)
    return NodeInfoResponse()


def _request_to_node_info(request: NodeInfoRequest) -> NodeInfo:
    return NodeInfo(
        gpu_model=request.gpu_model,
        vram=request.vram,
        cpu_model=request.cpu_model,
        ram=request.ram,
        network_speed=request.network_speed,
        operating_system=request.operating_system,
    )
