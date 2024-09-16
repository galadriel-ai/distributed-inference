import time

from distributedinference.domain.node.entities import NodeInfo
from distributedinference.domain.user.entities import User
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.node.entities import GetNodeInfoResponse


async def execute(
    user: User, node_info: NodeInfo, repository: NodeRepository
) -> GetNodeInfoResponse:
    connected_node = repository.get_connected_node_info(user.uid)
    return GetNodeInfoResponse(
        node_id=str(node_info.node_id),
        name_alias=node_info.name_alias,
        gpu_model=node_info.gpu_model,
        vram=node_info.vram,
        cpu_model=node_info.cpu_model,
        cpu_count=node_info.cpu_count,
        ram=node_info.ram,
        network_download_speed=node_info.network_download_speed,
        network_upload_speed=node_info.network_upload_speed,
        operating_system=node_info.operating_system,
        status="online" if connected_node else "offline",
        run_duration_seconds=(
            0 if not connected_node else int(time.time() - connected_node.connected_at)
        ),
        node_created_at=int(node_info.created_at.timestamp()),
    )
