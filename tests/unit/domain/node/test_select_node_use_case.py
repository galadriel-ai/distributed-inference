import asyncio
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import UUID

import pytest
from uuid_extensions import uuid7

import distributedinference.domain.node.select_node_use_case as use_case
import settings
from distributedinference.domain.node.entities import BackendHost
from distributedinference.domain.node.entities import ConnectedNode
from distributedinference.domain.node.entities import NodeStatus
from distributedinference.repository.connected_node_repository import (
    ConnectedNodeRepository,
)

UUIDS = [
    UUID("06752f3c-14a1-7837-8000-dfbea843ac25"),
    UUID("06752f3c-1bba-702f-8000-4c55b6de8aa8"),
    UUID("06752f3c-210c-7cdd-8000-d3f691af54fa"),
    UUID("06752f3c-27c1-7cd5-8000-94143d4da54b"),
    UUID("06752f3c-2d8f-7062-8000-0d4b8e7e2535"),
]


@pytest.fixture
def connected_node_repository() -> AsyncMock(spec=ConnectedNodeRepository):
    repository = AsyncMock(spec=ConnectedNodeRepository)
    repository.register_node = MagicMock(return_value=True)
    return repository


def _create_node(uid: UUID, model: str) -> ConnectedNode:
    return ConnectedNode(
        uid=uid,
        user_id=uuid7(),
        model=model,
        vram=16000,
        connected_at=123,
        websocket=MagicMock(),
        request_incoming_queues={},
        node_status=NodeStatus.RUNNING,
        connected_host=BackendHost.DISTRIBUTED_INFERENCE_EU,
    )


def test_select_node_with_no_nodes(connected_node_repository):
    assert use_case.execute("model", connected_node_repository) is None


def test_select_node_with_one_node(connected_node_repository):
    connected_node_repository.get_nodes_by_model.return_value = [
        _create_node(UUIDS[0], "model"),
    ]

    selected_node = use_case.execute("model", connected_node_repository)
    assert selected_node.uid == UUIDS[0]
    assert selected_node.model == "model"


def test_select_node_with_multiple_nodes(connected_node_repository):
    connected_node_repository.get_nodes_by_model.return_value = [
        _create_node(UUIDS[0], "model"),
        _create_node(UUIDS[1], "model"),
    ]

    selected_node = use_case.execute("model", connected_node_repository)
    assert selected_node.uid in [UUIDS[0], UUIDS[1]]
    assert selected_node.model == "model"


def test_select_node_after_reaching_maximum_parallel_requests(
    connected_node_repository,
):
    node = _create_node(UUIDS[0], "model")
    connected_node_repository.get_nodes_by_model.return_value = [node]
    for i in range(settings.MAX_PARALLEL_REQUESTS_PER_NODE - 1):
        node.request_incoming_queues[f"{i}"] = asyncio.Queue()

    # Initially, it should return the node
    assert use_case.execute("model", connected_node_repository).uid == UUIDS[0]

    # Add one more request
    node.request_incoming_queues[settings.MAX_PARALLEL_REQUESTS_PER_NODE - 1] = (
        asyncio.Queue()
    )

    # Now, there are no nodes left, should return None
    assert use_case.execute("model", connected_node_repository) is None


def test_select_datacenter_node_after_reaching_maximum_parallel_requests(
    connected_node_repository,
):
    node = _create_node(UUIDS[0], "model")
    node.vram = 2_000_000_000  # Datacenter GPU vRam
    connected_node_repository.get_nodes_by_model.return_value = [node]
    for i in range(settings.MAX_PARALLEL_REQUESTS_PER_DATACENTER_NODE - 1):
        node.request_incoming_queues[f"{i}"] = asyncio.Queue()

    # Initially, it should return the node
    assert use_case.execute("model", connected_node_repository).uid == UUIDS[0]

    # Add one more request
    node.request_incoming_queues[
        settings.MAX_PARALLEL_REQUESTS_PER_DATACENTER_NODE - 1
    ] = asyncio.Queue()

    # Now, there are no nodes left, should return None
    assert use_case.execute("model", connected_node_repository) is None


def test_8gb_node_handles_only_1_connection(connected_node_repository):
    node = _create_node(UUIDS[0], "model")
    node.vram = 1  # Small vRam
    connected_node_repository.get_nodes_by_model.return_value = [node]

    # Adding one request
    node.request_incoming_queues["test-id"] = asyncio.Queue()

    # Initially, it should return the node
    assert use_case.execute("model", connected_node_repository).uid == UUIDS[0]

    # Add one more request
    node.request_incoming_queues["test-id-2"] = asyncio.Queue()

    # Now, there are no nodes left, should return None
    assert use_case.execute("model", connected_node_repository) is None


def test_select_node_skips_unhealthy_not_self_hosted_nodes(connected_node_repository):
    node = _create_node(UUIDS[0], "model")
    node.node_status = NodeStatus.RUNNING_DEGRADED
    connected_node_repository.get_nodes_by_model.return_value = [node]
    assert use_case.execute("model", connected_node_repository) is None


def test_select_node_does_not_skip_unhealthy_self_hosted_nodes(
    connected_node_repository,
):
    node = _create_node(UUIDS[0], "model")
    node.node_status = NodeStatus.RUNNING_DEGRADED
    node.is_self_hosted = True
    connected_node_repository.get_nodes_by_model.return_value = [node]
    assert use_case.execute("model", connected_node_repository).uid == UUIDS[0]


def test_select_node_with_busy_nodes(connected_node_repository):
    node1 = _create_node(UUIDS[0], "model")
    node2 = _create_node(UUIDS[1], "model")
    node3 = _create_node(UUIDS[2], "model")
    connected_node_repository.get_nodes_by_model.return_value = [node1, node2, node3]

    with patch(
        "distributedinference.domain.node.entities.ConnectedNode.active_requests_count",
        side_effect=[
            settings.MAX_PARALLEL_REQUESTS_PER_NODE,
            settings.MAX_PARALLEL_REQUESTS_PER_NODE - 5,
            settings.MAX_PARALLEL_REQUESTS_PER_NODE,
            settings.MAX_PARALLEL_REQUESTS_PER_NODE - 5,
            settings.MAX_PARALLEL_REQUESTS_PER_NODE - 5,
        ],
    ):
        # Only node2 should be available since its active_requests_count is below the max
        selected_node = use_case.execute("model", connected_node_repository)
        assert selected_node.uid == UUIDS[1]


@patch("random.choice")
def test_all_busy_node_selection(connected_node_repository):
    node1 = _create_node(UUIDS[0], "model")
    node2 = _create_node(UUIDS[1], "model")
    node3 = _create_node(UUIDS[2], "model")
    connected_node_repository.get_nodes_by_model.return_value = [node1, node2, node3]

    with patch(
        "distributedinference.domain.node.entities.ConnectedNode.active_requests_count",
        side_effect=[
            settings.MAX_PARALLEL_REQUESTS_PER_NODE,
            settings.MAX_PARALLEL_REQUESTS_PER_NODE,
            settings.MAX_PARALLEL_REQUESTS_PER_NODE,
        ],
    ):
        # All nodes are busy, should return None
        selected_node = use_case.execute("model", connected_node_repository)
        assert selected_node is None


@patch("random.choice")
def test_random_node_selection(mock_random_choice, connected_node_repository):
    node1 = _create_node(UUIDS[0], "model")
    node2 = _create_node(UUIDS[1], "model")
    node3 = _create_node(UUIDS[2], "model")
    connected_node_repository.get_nodes_by_model.return_value = [node1, node2, node3]

    with patch(
        "distributedinference.domain.node.entities.ConnectedNode.active_requests_count",
        side_effect=[3, 3, 10, 3, 3, 3, 3],
    ):
        use_case.execute("model", connected_node_repository)
        mock_random_choice.assert_called_once_with([node1, node2])
