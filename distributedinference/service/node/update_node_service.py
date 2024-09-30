from mnemonic import Mnemonic

from distributedinference.domain.node.entities import NodeInfo
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.node.entities import UpdateNodeRequest
from distributedinference.service.node.entities import UpdateNodeResponse


async def execute(
    request: UpdateNodeRequest,
    node_info: NodeInfo,
    repository: NodeRepository,
) -> UpdateNodeResponse:
    await repository.update_node_name_alias(node_info.node_id, request.node_name)
    return UpdateNodeResponse()


def _generate_name() -> str:
    mnemo = Mnemonic("english")
    return "_".join(mnemo.generate(strength=128).split(" ")[:5])
