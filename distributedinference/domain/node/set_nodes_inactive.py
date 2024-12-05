from distributedinference import api_logger
from distributedinference.domain.node import node_status_transition
from distributedinference.domain.node.node_status_transition import NodeStatusEvent
from distributedinference.repository.node_repository import NodeRepository

logger = api_logger.get()


async def execute(
    node_repository: NodeRepository,
) -> None:
    logger.info(
        "Setting all connected nodes to stop status and cleaning up the connection timestamps..."
    )

    # Set all locally connected nodes to STOP status
    for node_id in node_repository.get_locally_connected_node_keys():
        status = await node_status_transition.execute(
            node_repository=node_repository,
            node_id=node_id,
            event=NodeStatusEvent.STOP,
        )
        if not node_repository.set_local_node_status(node_id, status):
            logger.error(
                f"Failed to set local node {node_id} to status {status}: Node not found in local node list"
            )

    await node_repository.set_all_connected_nodes_inactive()
