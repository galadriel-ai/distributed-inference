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
        gpu_model=node_info.specs.gpu_model if node_info.specs else None,
        vram=node_info.specs.vram if node_info.specs else None,
        gpu_count=node_info.specs.gpu_count if node_info.specs else None,
        cpu_model=node_info.specs.cpu_model if node_info.specs else None,
        cpu_count=node_info.specs.cpu_count if node_info.specs else None,
        ram=node_info.specs.ram if node_info.specs else None,
        network_download_speed=(
            node_info.specs.network_download_speed if node_info.specs else None
        ),
        network_upload_speed=(
            node_info.specs.network_upload_speed if node_info.specs else None
        ),
        operating_system=node_info.specs.operating_system if node_info.specs else None,
        status=status.description(),
        run_duration_seconds=(0 if not node_metrics else node_metrics.current_uptime),
        node_created_at=(
            0 if not node_info.created_at else int(node_info.created_at.timestamp())
        ),
        version=node_info.specs.version if node_info.specs else None,
    )
