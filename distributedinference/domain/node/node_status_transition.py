from enum import Enum
from typing import Optional
from uuid import UUID

from distributedinference.api_logger import api_logger
from distributedinference.domain.node.entities import ModelType, NodeStatus
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
    NodeStatus.STOPPED_DISABLED: NodeStatus.RUNNING_DISABLED,
    # If already running status need to keep the same status
    NodeStatus.RUNNING: NodeStatus.RUNNING,
    NodeStatus.RUNNING_BENCHMARKING: NodeStatus.RUNNING_BENCHMARKING,
    NodeStatus.RUNNING_DEGRADED: NodeStatus.RUNNING_DEGRADED,
    NodeStatus.RUNNING_DISABLED: NodeStatus.RUNNING_DISABLED,
}

STOP_TRANSITIONS = {
    NodeStatus.RUNNING: NodeStatus.STOPPED,
    NodeStatus.RUNNING_BENCHMARKING: NodeStatus.STOPPED_BENCHMARK_FAILED,
    NodeStatus.RUNNING_DEGRADED: NodeStatus.STOPPED_DEGRADED,
    NodeStatus.RUNNING_DISABLED: NodeStatus.STOPPED_DISABLED,
    NodeStatus.STOPPED_DISABLED: NodeStatus.STOPPED_DISABLED,
}

DEGRADED_TRANSITIONS = {
    NodeStatus.RUNNING: NodeStatus.RUNNING_DEGRADED,
    NodeStatus.RUNNING_BENCHMARKING: NodeStatus.RUNNING_BENCHMARKING,
    NodeStatus.RUNNING_DEGRADED: NodeStatus.RUNNING_DEGRADED,
    # Should not be possible
    NodeStatus.RUNNING_DISABLED: NodeStatus.RUNNING_DISABLED,
    NodeStatus.STOPPED_DISABLED: NodeStatus.STOPPED_DISABLED,
}

logger = api_logger.get()


async def execute(
    node_repository: NodeRepository,
    node_id: UUID,
    event: NodeStatusEvent,
    node_model_type: Optional[ModelType] = None,
) -> NodeStatus:
    status = await node_repository.get_node_status(node_id=node_id)

    # TODO: what if status in incorrect state?
    if event == event.START:
        # TODO: skip_benchmarking is a temp feature for image generation nodes only
        if node_model_type is ModelType.DIFFUSION:
            logger.info(
                f"Node {node_id} is with a diffusion model, skipping benchmarking"
            )
            return NodeStatus.RUNNING
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
