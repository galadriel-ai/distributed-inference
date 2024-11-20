from enum import Enum
from uuid import UUID

from distributedinference import api_logger
from distributedinference.domain.node.entities import NodeStatus
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service import error_responses


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
    NodeStatus.RUNNING_BENCHMARKING: NodeStatus.RUNNING_BENCHMARKING,
    NodeStatus.RUNNING_DEGRADED: NodeStatus.RUNNING_DEGRADED,
}

logger = api_logger.get()


async def execute(
    node_repository: NodeRepository, node_id: UUID, event: NodeStatusEvent
) -> NodeStatus:
    status = await node_repository.get_node_status(node_id=node_id)

    # TODO: what if status in incorrect state?
    if event == event.START:
        status = START_TRANSITIONS.get(status)
        if not status:
            _print_error(status, event)
            status = NodeStatus.RUNNING
        return status
    if event == event.STOP:
        status = STOP_TRANSITIONS.get(status)
        if not status:
            _print_error(status, event)
            status = NodeStatus.STOPPED_DEGRADED
        return status
    if event == event.DEGRADED:
        status = DEGRADED_TRANSITIONS.get(status)
        if not status:
            _print_error(status, event)
            status = NodeStatus.STOPPED_DEGRADED
        return status
    raise error_responses.InternalServerAPIError()


def _print_error(status, event):
    logger.error(
        f"Failed to do a valid Node Status Transition, current status: {status}"
        f", event: {event}"
    )
