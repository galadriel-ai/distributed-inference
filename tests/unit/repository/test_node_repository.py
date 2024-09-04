import asyncio
import pytest
from unittest.mock import MagicMock, patch, call
from uuid_extensions import uuid7

from distributedinference.domain.node.entities import NodeInfo
from distributedinference.domain.node.entities import NodeMetrics
from distributedinference.domain.node.entities import ConnectedNode
from distributedinference.repository.node_repository import (
    SQL_INSERT_OR_UPDATE_NODE_INFO,
    SQL_INSERT_OR_UPDATE_NODE_METRICS,
)
from distributedinference.repository.node_repository import NodeRepository

MAX_PARALLEL_REQUESTS = 10


@pytest.fixture
def node_repository():
    return NodeRepository(MAX_PARALLEL_REQUESTS)


@pytest.fixture
def mock_websocket():
    return MagicMock()


@pytest.fixture
def connected_node_factory(mock_websocket):
    def _create_node(uid, model="model"):
        return ConnectedNode(uid, model, mock_websocket, {}, MagicMock())

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


async def test_save_node_info(node_repository):
    node_id = uuid7()

    node_info = NodeInfo(
        gpu_model="NVIDIA GTX 1080",
        vram=8,
        cpu_model="Intel i7",
        cpu_count=8,
        ram=16,
        network_download_speed=1000,
        network_upload_speed=1000,
        operating_system="Linux",
    )

    with patch("distributedinference.repository.connection.write") as mock_write:
        await node_repository.save_node_info(node_id, node_info)
        mock_write.assert_called_once()
        args, kwargs = mock_write.call_args

        assert args[0] == SQL_INSERT_OR_UPDATE_NODE_INFO

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


async def test_save_node_metrics(node_repository):
    node_id = uuid7()

    node_metrics = NodeMetrics(requests_served=100, time_to_first_token=0.5)

    with patch("distributedinference.repository.connection.write") as mock_write:
        await node_repository.save_node_metrics(node_id, node_metrics)

        mock_write.assert_called_once()

        args, kwargs = mock_write.call_args

        assert args[0] == SQL_INSERT_OR_UPDATE_NODE_METRICS

        data = args[1]
        assert data["user_profile_id"] == node_id
        assert data["requests_served"] == await node_metrics.get_requests_served()
        assert (
            data["time_to_first_token"] == await node_metrics.get_time_to_first_token()
        )
        assert data["uptime"] == await node_metrics.get_uptime()
        assert "created_at" in data
        assert "last_updated_at" in data


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
        ],
    ):
        # Only node2 should be available since its active_requests_count is below the max
        selected_node = node_repository.select_node("model")
        assert selected_node.uid == "2"


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
        side_effect=[7, 3, 10],
    ):
        node_repository.select_node("model")
        mock_random_choice.assert_called_once_with([node1, node2])
