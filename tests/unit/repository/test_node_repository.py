import asyncio
import time
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import UUID, uuid1

import pytest
from uuid_extensions import uuid7

from distributedinference.domain.node.entities import ConnectedNode
from distributedinference.domain.node.entities import NodeInfo
from distributedinference.domain.node.entities import NodeMetricsIncrement
from distributedinference.domain.node.entities import InferenceStatusCodes
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.node_repository import (
    SQL_INCREMENT_NODE_METRICS,
)
from distributedinference.repository.node_repository import (
    SQL_UPDATE_NODE_INFO,
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
def node_repository(session_provider):
    return NodeRepository(
        session_provider, MAX_PARALLEL_REQUESTS, MAX_PARALLEL_DATACENTER_REQUESTS
    )


@pytest.fixture
def mock_websocket():
    return MagicMock()


@pytest.fixture
def connected_node_factory(mock_websocket):
    def _create_node(uid, model="model", small_node=False, datacenter_node=False):
        vram = 8000 if small_node else 16000
        if datacenter_node:
            vram = 90000
        return ConnectedNode(
            uid, uuid1(), model, vram, int(time.time()), mock_websocket, {}
        )

    return _create_node


def test_register_node(node_repository, connected_node_factory):
    node1 = connected_node_factory("1")
    node_repository.register_node(node1)

    assert node_repository._connected_nodes["1"] == node1
    assert len(node_repository._connected_nodes) == 1


def test_deregister_node(node_repository, connected_node_factory):
    node1 = connected_node_factory("1")
    node_repository.register_node(node1)

    node_repository.deregister_node("1")

    assert "1" not in node_repository._connected_nodes
    assert len(node_repository._connected_nodes) == 0


def test_select_node_with_no_nodes(node_repository):
    assert node_repository.select_node("model") is None


def test_select_node_with_nodes(node_repository, connected_node_factory):
    node1 = connected_node_factory("1")
    node2 = connected_node_factory("2")

    node_repository.register_node(node1)
    node_repository.register_node(node2)

    selected_node = node_repository.select_node("model")
    assert selected_node.uid in ["1", "2"]
    assert selected_node.model == "model"


def test_select_node_with_nodes_hosting_different_models(
    node_repository, connected_node_factory
):
    node1 = connected_node_factory("1", "model1")
    node2 = connected_node_factory("2", "model2")

    node_repository.register_node(node1)
    node_repository.register_node(node2)

    selected_node = node_repository.select_node("model1")
    assert selected_node.uid == "1"
    assert selected_node.model == "model1"

    selected_node = node_repository.select_node("model2")
    assert selected_node.uid == "2"
    assert selected_node.model == "model2"

    selected_node = node_repository.select_node("model3")
    assert selected_node is None


def test_select_node_but_unavailable_model(node_repository, connected_node_factory):
    node1 = connected_node_factory("1")

    node_repository.register_node(node1)

    selected_node = node_repository.select_node("model2")
    assert selected_node is None


def test_select_node_after_deregistration(node_repository, connected_node_factory):
    node1 = connected_node_factory("1")
    node2 = connected_node_factory("2")
    node3 = connected_node_factory("3")

    node_repository.register_node(node1)
    node_repository.register_node(node2)
    node_repository.register_node(node3)

    # Initially, it should return node1
    assert node_repository.select_node("model").uid in ["1", "2", "3"]
    assert len(node_repository._connected_nodes) == 3

    node_repository.deregister_node("1")
    # Now, it should return node2
    assert node_repository.select_node("model").uid in ["2", "3"]
    assert len(node_repository._connected_nodes) == 2

    node_repository.deregister_node("2")
    # Now, it should return node3
    assert node_repository.select_node("model").uid == "3"
    assert len(node_repository._connected_nodes) == 1

    node_repository.deregister_node("3")
    # Now, there are no nodes left, should return None
    assert node_repository.select_node("model") is None
    assert len(node_repository._connected_nodes) == 0


def test_select_node_after_reaching_maximum_parallel_requests(
    node_repository, connected_node_factory
):
    node = connected_node_factory("1")
    node_repository.register_node(node)

    for i in range(MAX_PARALLEL_REQUESTS - 1):
        node.request_incoming_queues[i] = asyncio.Queue()

    # Initially, it should return the node
    assert node_repository.select_node("model").uid == "1"

    # Add one more request
    node.request_incoming_queues[MAX_PARALLEL_REQUESTS - 1] = asyncio.Queue()

    # Now, there are no nodes left, should return None
    assert node_repository.select_node("model") is None


def test_select_datacenter_node_after_reaching_maximum_parallel_requests(
    node_repository, connected_node_factory
):
    node = connected_node_factory("1", datacenter_node=True)
    node_repository.register_node(node)

    for i in range(MAX_PARALLEL_DATACENTER_REQUESTS - 1):
        node.request_incoming_queues[f"{i}"] = asyncio.Queue()

    # Initially, it should return the node
    assert node_repository.select_node("model").uid == "1"

    # Add one more request
    node.request_incoming_queues[f"{MAX_PARALLEL_DATACENTER_REQUESTS - 1}"] = (
        asyncio.Queue()
    )

    # Now, there are no nodes left, should return None
    assert node_repository.select_node("model") is None


def test_8gb_node_handles_only_1_connection(node_repository, connected_node_factory):
    node = connected_node_factory("1", small_node=True)
    node_repository.register_node(node)

    # Adding one request
    node.request_incoming_queues["test-id"] = asyncio.Queue()

    # Initially, it should return the node
    assert node_repository.select_node("model").uid == "1"

    # Add one more request
    node.request_incoming_queues["test-id-2"] = asyncio.Queue()

    # Now, there are no nodes left, should return None
    assert node_repository.select_node("model") is None


async def test_save_node_info(node_repository, session_provider):
    node_id = uuid7()

    node_info = NodeInfo(
        name="name",
        name_alias="user alias",
        node_id=NODE_UUID,
        gpu_model="NVIDIA GTX 1080",
        vram=8,
        cpu_model="Intel i7",
        cpu_count=8,
        ram=16,
        network_download_speed=1000,
        network_upload_speed=1000,
        operating_system="Linux",
    )

    mock_session = AsyncMock()
    session_provider.get.return_value.__aenter__.return_value = mock_session

    await node_repository.save_node_info(node_id, node_info)

    mock_session.execute.assert_called_once()
    args, kwargs = mock_session.execute.call_args

    assert args[0].text == SQL_UPDATE_NODE_INFO

    data = args[1]
    assert data["user_profile_id"] == node_id
    assert data["gpu_model"] == node_info.gpu_model
    assert data["vram"] == node_info.vram
    assert data["cpu_model"] == node_info.cpu_model
    assert data["cpu_count"] == node_info.cpu_count
    assert data["ram"] == node_info.ram
    assert data["network_download_speed"] == node_info.network_download_speed
    assert data["network_upload_speed"] == node_info.network_upload_speed
    assert data["operating_system"] == node_info.operating_system
    assert "created_at" in data
    assert "last_updated_at" in data

    mock_session.commit.assert_called_once()


async def test_save_node_metrics(node_repository, session_provider):
    node_id = uuid7()

    node_metrics = NodeMetricsIncrement(
        node_id=node_id,
        requests_served_incerement=100,
        time_to_first_token=0.5,
        inference_tokens_per_second=30.5,
    )

    mock_session = AsyncMock()
    session_provider.get.return_value.__aenter__.return_value = mock_session

    await node_repository.increment_node_metrics(node_metrics)

    mock_session.execute.assert_called_once()
    args, kwargs = mock_session.execute.call_args

    assert args[0].text == SQL_INCREMENT_NODE_METRICS

    data = args[1]
    assert data["node_id"] == node_id
    assert data["requests_served_increment"] == node_metrics.requests_served_incerement
    assert (
        data["requests_successful_increment"]
        == node_metrics.requests_successful_incerement
    )
    assert data["requests_failed_increment"] == node_metrics.requests_failed_increment
    assert data["time_to_first_token"] == node_metrics.time_to_first_token
    assert (
        data["inference_tokens_per_second"] == node_metrics.inference_tokens_per_second
    )
    assert data["uptime_increment"] == node_metrics.uptime_increment
    assert "created_at" in data
    assert "last_updated_at" in data

    # Check if the commit was called
    mock_session.commit.assert_called_once()


def test_select_node_with_busy_nodes(node_repository, connected_node_factory):
    node1 = connected_node_factory("1")
    node2 = connected_node_factory("2")
    node3 = connected_node_factory("3")

    node_repository.register_node(node1)
    node_repository.register_node(node2)
    node_repository.register_node(node3)

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
        selected_node = node_repository.select_node("model")
        assert selected_node.uid == "2"


@patch("random.choice")
def test_all_busy_node_selection(
    mock_random_choice, node_repository, connected_node_factory
):
    node1 = connected_node_factory("1")
    node2 = connected_node_factory("2")
    node3 = connected_node_factory("3")

    node_repository.register_node(node1)
    node_repository.register_node(node2)
    node_repository.register_node(node3)

    with patch(
        "distributedinference.domain.node.entities.ConnectedNode.active_requests_count",
        side_effect=[
            MAX_PARALLEL_REQUESTS,
            MAX_PARALLEL_REQUESTS,
            MAX_PARALLEL_REQUESTS,
        ],
    ):
        # All nodes are busy, should return None
        selected_node = node_repository.select_node("model")
        assert selected_node is None


@patch("random.choice")
def test_random_node_selection(
    mock_random_choice, node_repository, connected_node_factory
):
    node1 = connected_node_factory("1")
    node2 = connected_node_factory("2")
    node3 = connected_node_factory("3")

    node_repository.register_node(node1)
    node_repository.register_node(node2)
    node_repository.register_node(node3)

    with patch(
        "distributedinference.domain.node.entities.ConnectedNode.active_requests_count",
        side_effect=[3, 3, 10, 3, 3, 3, 3],
    ):
        node_repository.select_node("model")
        mock_random_choice.assert_called_once_with([node1, node2])


async def test_deregister_node_sends_error_on_disconnect(
    node_repository, connected_node_factory
):
    node_id = "1"
    request_id = "request_123"
    node = connected_node_factory(node_id)

    request_queue = asyncio.Queue()
    node.request_incoming_queues[request_id] = request_queue
    node_repository.register_node(node)

    assert node_id in node_repository._connected_nodes

    node_repository.deregister_node(node_id)

    assert node_id not in node_repository._connected_nodes

    error_response = await request_queue.get()

    assert error_response["request_id"] == request_id
    assert error_response["error"]["message"] == "Node disconnected"
    assert (
        error_response["error"]["status_code"]
        == InferenceStatusCodes.UNPROCESSABLE_ENTITY.value
    )
