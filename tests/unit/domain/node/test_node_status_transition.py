from typing import Optional
from unittest.mock import AsyncMock
from uuid import UUID

from distributedinference.domain.node import node_status_transition
from distributedinference.domain.node.entities import NodeStatus
from distributedinference.domain.node.node_status_transition import NodeStatusEvent
from distributedinference.repository.node_repository import NodeRepository

NODE_ID = UUID("f8f7e008-9f2b-40ef-9368-c062b7785272")


def _get_node_repository(return_status: Optional[NodeStatus]) -> NodeRepository:
    node_repository = AsyncMock(spec=NodeRepository)
    node_repository.get_node_status = AsyncMock(return_value=return_status)
    return node_repository


async def test_transitions():
    # Event, Current Status, Expected Status after transition
    transitions = [
        # Start
        (NodeStatusEvent.START, None, NodeStatus.RUNNING_BENCHMARKING),
        (NodeStatusEvent.START, NodeStatus.RUNNING, NodeStatus.RUNNING),
        (
            NodeStatusEvent.START,
            NodeStatus.RUNNING_BENCHMARKING,
            NodeStatus.RUNNING_BENCHMARKING,
        ),
        (
            NodeStatusEvent.START,
            NodeStatus.RUNNING_DEGRADED,
            NodeStatus.RUNNING_DEGRADED,
        ),
        (NodeStatusEvent.START, NodeStatus.STOPPED, NodeStatus.RUNNING),
        (
            NodeStatusEvent.START,
            NodeStatus.STOPPED_BENCHMARK_FAILED,
            NodeStatus.RUNNING_BENCHMARKING,
        ),
        (
            NodeStatusEvent.START,
            NodeStatus.STOPPED_DEGRADED,
            NodeStatus.RUNNING_BENCHMARKING,
        ),
        # Stop
        (NodeStatusEvent.STOP, NodeStatus.RUNNING, NodeStatus.STOPPED),
        (
            NodeStatusEvent.STOP,
            NodeStatus.RUNNING_BENCHMARKING,
            NodeStatus.STOPPED_BENCHMARK_FAILED,
        ),
        (
            NodeStatusEvent.STOP,
            NodeStatus.RUNNING_DEGRADED,
            NodeStatus.STOPPED_DEGRADED,
        ),
        # Degraded
        (NodeStatusEvent.DEGRADED, NodeStatus.RUNNING, NodeStatus.RUNNING_DEGRADED),
        (
            NodeStatusEvent.DEGRADED,
            NodeStatus.RUNNING_BENCHMARKING,
            NodeStatus.STOPPED_BENCHMARK_FAILED,  # STOP EVENT!
        ),
        (
            NodeStatusEvent.DEGRADED,
            NodeStatus.RUNNING_DEGRADED,
            NodeStatus.RUNNING_DEGRADED,
        ),
    ]

    for event, status, expected in transitions:
        node_repository = _get_node_repository(status)
        result = await node_status_transition.execute(node_repository, NODE_ID, event)
        print(f"UnitTest, event: {event}, status: {status}, expected: {expected}")
        assert result == expected
