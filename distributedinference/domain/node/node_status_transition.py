from enum import Enum
from typing import Optional
from uuid import UUID

from distributedinference.domain.node.entities import NodeStatus
from distributedinference.repository.node_repository import NodeRepository


class NodeStatusEvent(Enum):
    START = 1
    STOP = 2
    BENCHMARK_SUCCEED = 3
    BENCHMARK_FAIL = 4
    DEGRADED = 5


START_TRANSITIONS = {
    None: NodeStatus.RUNNING_BENCHMARKING,
    NodeStatus.STOPPED_DEGRADED: NodeStatus.RUNNING_BENCHMARKING,
    NodeStatus.STOPPED_BENCHMARK_FAILED: NodeStatus.RUNNING_BENCHMARKING,
    NodeStatus.STOPPED: NodeStatus.RUNNING,
}

STOP_TRANSITIONS = {
    NodeStatus.RUNNING: NodeStatus.STOPPED,
    NodeStatus.RUNNING_BENCHMARKING: NodeStatus.STOPPED_BENCHMARK_FAILED,
    NodeStatus.RUNNING_DEGRADED: NodeStatus.STOPPED_DEGRADED,
}


async def execute(
    node_repository: NodeRepository, node_id: UUID, event: NodeStatusEvent
) -> Optional[NodeStatus]:
    status = await node_repository.get_node_status(node_id=node_id)

    if event == event.START:
        return START_TRANSITIONS.get(status)
    if event == event.STOP:
        return STOP_TRANSITIONS.get(status)
    if event == event.BENCHMARK_SUCCEED:
        if status == NodeStatus.RUNNING_BENCHMARKING:
            return NodeStatus.RUNNING
    if event == event.BENCHMARK_FAIL:
        if status == NodeStatus.RUNNING_BENCHMARKING:
            return NodeStatus.STOPPED_BENCHMARK_FAILED
    if event == event.DEGRADED:
        if status == NodeStatus.RUNNING:
            return NodeStatus.RUNNING_DEGRADED
