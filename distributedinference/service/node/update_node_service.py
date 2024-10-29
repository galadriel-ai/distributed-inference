from distributedinference.domain.node.entities import NodeInfo
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.node.entities import UpdateNodeRequest
from distributedinference.service.node.entities import UpdateNodeResponse


async def execute(
    request: UpdateNodeRequest,
    node_info: NodeInfo,
    repository: NodeRepository,
) -> UpdateNodeResponse:
    is_name_updated = False
    is_archival_status_updated = False
    if request.node_name:
        await repository.update_node_name_alias(node_info.node_id, request.node_name)
        is_name_updated = True
    if request.is_archived is not None:
        await repository.update_node_archival_status(
            node_info.node_id, request.is_archived
        )
        is_archival_status_updated = True
    return UpdateNodeResponse(
        is_name_updated=is_name_updated,
        is_archival_status_updated=is_archival_status_updated,
    )
