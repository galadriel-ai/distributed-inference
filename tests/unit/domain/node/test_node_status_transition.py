from typing import Optional
from unittest.mock import AsyncMock
from uuid import UUID

from distributedinference.domain.node import node_status_transition
from distributedinference.domain.node.entities import ModelType, NodeStatus
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
        (
            NodeStatusEvent.START,
            NodeStatus.RUNNING_DISABLED,
            NodeStatus.RUNNING_DISABLED,
        ),
        (
            NodeStatusEvent.START,
            NodeStatus.STOPPED_DISABLED,
            NodeStatus.RUNNING_DISABLED,
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
        (
            NodeStatusEvent.STOP,
            NodeStatus.RUNNING_DISABLED,
            NodeStatus.STOPPED_DISABLED,
        ),
        (
            NodeStatusEvent.STOP,
            NodeStatus.STOPPED_DISABLED,
            NodeStatus.STOPPED_DISABLED,
        ),
        # Degraded
        (NodeStatusEvent.DEGRADED, NodeStatus.RUNNING, NodeStatus.RUNNING_DEGRADED),
        (
            NodeStatusEvent.DEGRADED,
            NodeStatus.RUNNING_BENCHMARKING,
            NodeStatus.RUNNING_BENCHMARKING,
        ),
        (
            NodeStatusEvent.DEGRADED,
            NodeStatus.RUNNING_DEGRADED,
            NodeStatus.RUNNING_DEGRADED,
        ),
        (
            NodeStatusEvent.DEGRADED,
            NodeStatus.RUNNING_DISABLED,
            NodeStatus.RUNNING_DISABLED,
        ),
        (
            NodeStatusEvent.DEGRADED,
            NodeStatus.STOPPED_DISABLED,
            NodeStatus.STOPPED_DISABLED,
        ),
    ]

    for event, status, expected in transitions:
        node_repository = _get_node_repository(status)
        result = await node_status_transition.execute(node_repository, NODE_ID, event)
        print(f"UnitTest, event: {event}, status: {status}, expected: {expected}")
        assert result == expected


async def test_diffusion_node_transition():
    node_repository = _get_node_repository(None)
    result = await node_status_transition.execute(
        node_repository,
        NODE_ID,
        NodeStatusEvent.START,
        node_model_type=ModelType.DIFFUSION,
    )
    print(f"UnitTest, skip_benchmarking: {result}")
    assert result == NodeStatus.RUNNING


async def test_is_active():
    status = NodeStatus.RUNNING
    assert status.is_active()
    status = NodeStatus.RUNNING_DEGRADED
    assert status.is_active()
    status = NodeStatus.RUNNING_BENCHMARKING
    assert not status.is_active()
    status = NodeStatus.STOPPED
    assert not status.is_active()
    status = NodeStatus.STOPPED_BENCHMARK_FAILED
    assert not status.is_active()

async def test_is_connected():
    status = NodeStatus.RUNNING
    assert status.is_connected()
    status = NodeStatus.RUNNING_DEGRADED
    assert status.is_connected()
    status = NodeStatus.RUNNING_BENCHMARKING
    assert status.is_connected()
    status = NodeStatus.STOPPED
    assert not status.is_connected()
    status = NodeStatus.STOPPED_BENCHMARK_FAILED
    assert not status.is_connected()
