from uuid import UUID

from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.node.entities import CreateNodeRequest
from distributedinference.service.node.entities import CreateNodeResponse


async def execute(
    _: CreateNodeRequest, user_profile_id: UUID, repository: NodeRepository
) -> CreateNodeResponse:
    node_info = await repository.create_node(user_profile_id)
    return CreateNodeResponse(response="OK", node_id=str(node_info.node_id))
