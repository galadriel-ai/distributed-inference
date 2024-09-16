from uuid import UUID

from mnemonic import Mnemonic

from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.node.entities import CreateNodeRequest
from distributedinference.service.node.entities import CreateNodeResponse


async def execute(
    request: CreateNodeRequest, user_profile_id: UUID, repository: NodeRepository
) -> CreateNodeResponse:
    name = _generate_name()
    await repository.create_node(user_profile_id, name, request.node_name)
    return CreateNodeResponse(response="OK", node_id=name)


def _generate_name() -> str:
    mnemo = Mnemonic("english")
    return "_".join(mnemo.generate(strength=128).split(" ")[:5])
