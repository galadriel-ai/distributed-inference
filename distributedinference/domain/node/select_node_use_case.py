import random
from typing import Optional

import settings
from distributedinference.domain.node.entities import ConnectedNode
from distributedinference.repository.connected_node_repository import (
    ConnectedNodeRepository,
)


def execute(
    model: str, connected_node_repository: ConnectedNodeRepository
) -> Optional[ConnectedNode]:
    nodes = connected_node_repository.get_nodes_by_model(model)
    eligible_nodes = [node for node in nodes if _can_handle_new_request(node)]
    if not eligible_nodes:
        return None

    return random.choice(eligible_nodes)


def _can_handle_new_request(node: ConnectedNode) -> bool:
    if not node.is_self_hosted and not node.node_status.is_healthy():
        return False
    if node.is_datacenter_gpu():
        return (
            node.active_requests_count()
            < settings.MAX_PARALLEL_REQUESTS_PER_DATACENTER_NODE
        )
    if node.can_handle_parallel_requests():
        return node.active_requests_count() < settings.MAX_PARALLEL_REQUESTS_PER_NODE

    return node.active_requests_count() == 1
