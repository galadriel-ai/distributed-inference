import asyncio
import time
from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import UUID
from uuid import uuid1

import pytest

from distributedinference.domain.node.entities import ConnectedNode
from distributedinference.domain.node.entities import InferenceErrorStatusCodes
from distributedinference.domain.node.entities import NodeStatus
from distributedinference.repository.connected_node_repository import (
    ConnectedNodeRepository,
)
from distributedinference.repository.connection import SessionProvider

MAX_PARALLEL_REQUESTS = 10
MAX_PARALLEL_DATACENTER_REQUESTS = 20
NODE_UUID = UUID("40c95432-8b2c-4208-bdf4-84f49ff957a3")


@pytest.fixture
def session_provider():
    mock_session_provider = MagicMock(spec=SessionProvider)
    return mock_session_provider


@pytest.fixture
def connected_node_repository(session_provider):
    return ConnectedNodeRepository(
        MAX_PARALLEL_REQUESTS,
        MAX_PARALLEL_DATACENTER_REQUESTS,
    )


@pytest.fixture
def mock_websocket():
    return MagicMock()


@pytest.fixture
def connected_node_factory(mock_websocket):
    def _create_node(
        uid,
        model="model",
        small_node=False,
        datacenter_node=False,
        is_self_hosted=False,
        node_status=NodeStatus.RUNNING,
    ):
        vram = 8000 if small_node else 16000
        if datacenter_node:
            vram = 90000
        return ConnectedNode(
            uid,
            uuid1(),
            model,
            vram,
            int(time.time()),
            mock_websocket,
            {},
            node_status,
            is_self_hosted,
            None,
        )

    return _create_node


def test_register_node(connected_node_repository, connected_node_factory):
    node1 = connected_node_factory("1")
    connected_node_repository.register_node(node1)

    assert connected_node_repository._connected_nodes["1"] == node1
    assert len(connected_node_repository._connected_nodes) == 1


def test_deregister_node(connected_node_repository, connected_node_factory):
    node1 = connected_node_factory("1")
    connected_node_repository.register_node(node1)

    connected_node_repository.deregister_node("1")

    assert "1" not in connected_node_repository._connected_nodes
    assert len(connected_node_repository._connected_nodes) == 0


def test_select_node_with_no_nodes(connected_node_repository):
    assert connected_node_repository.select_node("model") is None


def test_select_node_with_nodes(connected_node_repository, connected_node_factory):
    node1 = connected_node_factory("1")
    node2 = connected_node_factory("2")

    connected_node_repository.register_node(node1)
    connected_node_repository.register_node(node2)

    selected_node = connected_node_repository.select_node("model")
    assert selected_node.uid in ["1", "2"]
    assert selected_node.model == "model"


def test_select_node_with_nodes_hosting_different_models(
    connected_node_repository, connected_node_factory
):
    node1 = connected_node_factory("1", "model1")
    node2 = connected_node_factory("2", "model2")

    connected_node_repository.register_node(node1)
    connected_node_repository.register_node(node2)

    selected_node = connected_node_repository.select_node("model1")
    assert selected_node.uid == "1"
    assert selected_node.model == "model1"

    selected_node = connected_node_repository.select_node("model2")
    assert selected_node.uid == "2"
    assert selected_node.model == "model2"

    selected_node = connected_node_repository.select_node("model3")
    assert selected_node is None


def test_select_node_but_unavailable_model(
    connected_node_repository, connected_node_factory
):
    node1 = connected_node_factory("1")

    connected_node_repository.register_node(node1)

    selected_node = connected_node_repository.select_node("model2")
    assert selected_node is None


def test_select_node_after_deregistration(
    connected_node_repository, connected_node_factory
):
    node1 = connected_node_factory("1")
    node2 = connected_node_factory("2")
    node3 = connected_node_factory("3")

    connected_node_repository.register_node(node1)
    connected_node_repository.register_node(node2)
    connected_node_repository.register_node(node3)

    # Initially, it should return node1
    assert connected_node_repository.select_node("model").uid in ["1", "2", "3"]
    assert len(connected_node_repository._connected_nodes) == 3

    connected_node_repository.deregister_node("1")
    # Now, it should return node2
    assert connected_node_repository.select_node("model").uid in ["2", "3"]
    assert len(connected_node_repository._connected_nodes) == 2

    connected_node_repository.deregister_node("2")
    # Now, it should return node3
    assert connected_node_repository.select_node("model").uid == "3"
    assert len(connected_node_repository._connected_nodes) == 1

    connected_node_repository.deregister_node("3")
    # Now, there are no nodes left, should return None
    assert connected_node_repository.select_node("model") is None
    assert len(connected_node_repository._connected_nodes) == 0


def test_select_node_after_reaching_maximum_parallel_requests(
    connected_node_repository, connected_node_factory
):
    node = connected_node_factory("1")
    connected_node_repository.register_node(node)

    for i in range(MAX_PARALLEL_REQUESTS - 1):
        node.request_incoming_queues[i] = asyncio.Queue()

    # Initially, it should return the node
    assert connected_node_repository.select_node("model").uid == "1"

    # Add one more request
    node.request_incoming_queues[MAX_PARALLEL_REQUESTS - 1] = asyncio.Queue()

    # Now, there are no nodes left, should return None
    assert connected_node_repository.select_node("model") is None


def test_select_datacenter_node_after_reaching_maximum_parallel_requests(
    connected_node_repository, connected_node_factory
):
    node = connected_node_factory("1", datacenter_node=True)
    connected_node_repository.register_node(node)

    for i in range(MAX_PARALLEL_DATACENTER_REQUESTS - 1):
        node.request_incoming_queues[f"{i}"] = asyncio.Queue()

    # Initially, it should return the node
    assert connected_node_repository.select_node("model").uid == "1"

    # Add one more request
    node.request_incoming_queues[f"{MAX_PARALLEL_DATACENTER_REQUESTS - 1}"] = (
        asyncio.Queue()
    )

    # Now, there are no nodes left, should return None
    assert connected_node_repository.select_node("model") is None


def test_8gb_node_handles_only_1_connection(
    connected_node_repository, connected_node_factory
):
    node = connected_node_factory("1", small_node=True)
    connected_node_repository.register_node(node)

    # Adding one request
    node.request_incoming_queues["test-id"] = asyncio.Queue()

    # Initially, it should return the node
    assert connected_node_repository.select_node("model").uid == "1"

    # Add one more request
    node.request_incoming_queues["test-id-2"] = asyncio.Queue()

    # Now, there are no nodes left, should return None
    assert connected_node_repository.select_node("model") is None


def test_select_node_skips_unhealthy_not_self_hosted_nodes(
    connected_node_repository, connected_node_factory
):
    node = connected_node_factory("1")
    node.node_status = NodeStatus.RUNNING_DEGRADED
    connected_node_repository.register_node(node)

    # It should return None
    assert connected_node_repository.select_node("model") is None


def test_select_node_does_not_skip_unhealthy_self_hosted_nodes(
    connected_node_repository, connected_node_factory
):
    node = connected_node_factory("1", is_self_hosted=True)
    connected_node_repository.register_node(node)

    # It should return the node
    assert connected_node_repository.select_node("model") == node


def test_select_node_with_busy_nodes(connected_node_repository, connected_node_factory):
    node1 = connected_node_factory("1")
    node2 = connected_node_factory("2")
    node3 = connected_node_factory("3")

    connected_node_repository.register_node(node1)
    connected_node_repository.register_node(node2)
    connected_node_repository.register_node(node3)

    with patch(
        "distributedinference.domain.node.entities.ConnectedNode.active_requests_count",
        side_effect=[
            MAX_PARALLEL_REQUESTS,
            MAX_PARALLEL_REQUESTS - 5,
            MAX_PARALLEL_REQUESTS,
            MAX_PARALLEL_REQUESTS - 5,
            MAX_PARALLEL_REQUESTS - 5,
        ],
    ):
        # Only node2 should be available since its active_requests_count is below the max
        selected_node = connected_node_repository.select_node("model")
        assert selected_node.uid == "2"


@patch("random.choice")
def test_all_busy_node_selection(
    mock_random_choice, connected_node_repository, connected_node_factory
):
    node1 = connected_node_factory("1")
    node2 = connected_node_factory("2")
    node3 = connected_node_factory("3")

    connected_node_repository.register_node(node1)
    connected_node_repository.register_node(node2)
    connected_node_repository.register_node(node3)

    with patch(
        "distributedinference.domain.node.entities.ConnectedNode.active_requests_count",
        side_effect=[
            MAX_PARALLEL_REQUESTS,
            MAX_PARALLEL_REQUESTS,
            MAX_PARALLEL_REQUESTS,
        ],
    ):
        # All nodes are busy, should return None
        selected_node = connected_node_repository.select_node("model")
        assert selected_node is None


@patch("random.choice")
def test_random_node_selection(
    mock_random_choice, connected_node_repository, connected_node_factory
):
    node1 = connected_node_factory("1")
    node2 = connected_node_factory("2")
    node3 = connected_node_factory("3")

    connected_node_repository.register_node(node1)
    connected_node_repository.register_node(node2)
    connected_node_repository.register_node(node3)

    with patch(
        "distributedinference.domain.node.entities.ConnectedNode.active_requests_count",
        side_effect=[3, 3, 10, 3, 3, 3, 3],
    ):
        connected_node_repository.select_node("model")
        mock_random_choice.assert_called_once_with([node1, node2])


async def test_deregister_node_sends_error_on_disconnect(
    connected_node_repository, connected_node_factory
):
    node_id = "1"
    request_id = "request_123"
    node = connected_node_factory(node_id)

    request_queue = asyncio.Queue()
    node.request_incoming_queues[request_id] = request_queue
    connected_node_repository.register_node(node)

    assert node_id in connected_node_repository._connected_nodes

    connected_node_repository.deregister_node(node_id)

    assert node_id not in connected_node_repository._connected_nodes

    error_response = await request_queue.get()

    assert error_response["request_id"] == request_id
    assert error_response["error"]["message"] == "Node disconnected"
    assert (
        error_response["error"]["status_code"]
        == InferenceErrorStatusCodes.UNPROCESSABLE_ENTITY.value
    )
