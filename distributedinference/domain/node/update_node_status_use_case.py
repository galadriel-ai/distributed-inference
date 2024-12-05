from uuid import UUID

from distributedinference.domain.node.entities import NodeStatus
from distributedinference.repository.connected_node_repository import (
    ConnectedNodeRepository,
)
from distributedinference.repository.node_repository import NodeRepository


async def execute(
    node_uid: UUID,
    status: NodeStatus,
    node_repository: NodeRepository,
    connected_node_repository: ConnectedNodeRepository,
) -> None:
    connected_node_repository.update_node_status(node_uid, status)
    await node_repository.update_node_status(node_uid, status)
