from distributedinference.domain.node.entities import NodeInfo
from distributedinference.domain.node.entities import NodeStatus
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.node.entities import GetNodeInfoResponse


async def execute(
    node_info: NodeInfo, repository: NodeRepository
) -> GetNodeInfoResponse:
    node_metrics = await repository.get_node_metrics(node_info.node_id)
    status = node_metrics.status if node_metrics else NodeStatus.STOPPED
    return GetNodeInfoResponse(
        node_id=str(node_info.node_id),
        name_alias=node_info.name_alias,
        gpu_model=node_info.gpu_model,
        vram=node_info.vram,
        gpu_count=node_info.gpu_count,
        cpu_model=node_info.cpu_model,
        cpu_count=node_info.cpu_count,
        ram=node_info.ram,
        network_download_speed=node_info.network_download_speed,
        network_upload_speed=node_info.network_upload_speed,
        operating_system=node_info.operating_system,
        status=status.description(),
        run_duration_seconds=(0 if not node_metrics else node_metrics.current_uptime),
        node_created_at=(
            0 if not node_info.created_at else int(node_info.created_at.timestamp())
        ),
        version=node_info.version,
    )
