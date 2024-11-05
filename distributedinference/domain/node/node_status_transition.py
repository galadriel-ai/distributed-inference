from enum import Enum
from typing import Optional
from uuid import UUID

from distributedinference import api_logger
from distributedinference.domain.node.entities import NodeStatus
from distributedinference.repository.node_repository import NodeRepository


class NodeStatusEvent(Enum):
    START = 1
    STOP = 2
    DEGRADED = 3


START_TRANSITIONS = {
    None: NodeStatus.RUNNING_BENCHMARKING,
    NodeStatus.STOPPED_DEGRADED: NodeStatus.RUNNING_BENCHMARKING,
    NodeStatus.STOPPED_BENCHMARK_FAILED: NodeStatus.RUNNING_BENCHMARKING,
    NodeStatus.STOPPED: NodeStatus.RUNNING,
    # If already running status need to keep the same status
    NodeStatus.RUNNING: NodeStatus.RUNNING,
    NodeStatus.RUNNING_BENCHMARKING: NodeStatus.RUNNING_BENCHMARKING,
    NodeStatus.RUNNING_DEGRADED: NodeStatus.RUNNING_DEGRADED,
}

STOP_TRANSITIONS = {
    NodeStatus.RUNNING: NodeStatus.STOPPED,
    NodeStatus.RUNNING_BENCHMARKING: NodeStatus.STOPPED_BENCHMARK_FAILED,
    NodeStatus.RUNNING_DEGRADED: NodeStatus.STOPPED_DEGRADED,
}

DEGRADED_TRANSITIONS = {
    NodeStatus.RUNNING: NodeStatus.RUNNING_DEGRADED,
    NodeStatus.RUNNING_BENCHMARKING: NodeStatus.STOPPED_BENCHMARK_FAILED,
    NodeStatus.RUNNING_DEGRADED: NodeStatus.RUNNING_DEGRADED,
}

logger = api_logger.get()


async def execute(
    node_repository: NodeRepository, node_id: UUID, event: NodeStatusEvent
) -> Optional[NodeStatus]:
    status = await node_repository.get_node_status(node_id=node_id)
    logger.debug(f"Node Status Transition, status: {status}, event: {event}")

    # TODO: what if status in incorrect state?
    if event == event.START:
        return START_TRANSITIONS.get(status)
    if event == event.STOP:
        return STOP_TRANSITIONS.get(status)
    if event == event.DEGRADED:
        return DEGRADED_TRANSITIONS.get(status)
