import asyncio
import time
from unittest.mock import MagicMock
from uuid import UUID
from uuid import uuid1

import pytest

from distributedinference.domain.node.entities import BackendHost, ConnectedNode
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
        "distributed-inference-us",
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
            BackendHost.from_value("distributed-inference-us"),
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


# TODO:
def test_get_nodes_by_models(connected_node_repository, connected_node_factory):
    node1 = connected_node_factory("1", "model1")
    node2 = connected_node_factory("2", "model2")

    connected_node_repository.register_node(node1)
    connected_node_repository.register_node(node2)

    selected_nodes = connected_node_repository.get_nodes_by_model("model1")
    assert len(selected_nodes) == 1
    assert selected_nodes[0].uid == "1"
    assert selected_nodes[0].model == "model1"

    selected_nodes = connected_node_repository.get_nodes_by_model("model2")
    assert len(selected_nodes) == 1
    assert selected_nodes[0].uid == "2"
    assert selected_nodes[0].model == "model2"

    selected_nodes = connected_node_repository.get_nodes_by_model("model3")
    assert selected_nodes == []


def test_select_node_but_unavailable_model(
    connected_node_repository, connected_node_factory
):
    node1 = connected_node_factory("1")

    connected_node_repository.register_node(node1)

    selected_nodes = connected_node_repository.get_nodes_by_model("model2")
    assert selected_nodes == []


def test_select_node_after_deregistration(
    connected_node_repository, connected_node_factory
):
    node_uids = ["1", "2", "3"]
    for node_uid in node_uids:
        node = connected_node_factory(node_uid)
        connected_node_repository.register_node(node)

    # Initially, it should return node1
    nodes = connected_node_repository.get_nodes_by_model("model")
    assert len(nodes) == 3
    for i in node_uids:
        assert i in [node.uid for node in nodes]

    connected_node_repository.deregister_node("1")
    nodes = connected_node_repository.get_nodes_by_model("model")
    assert len(nodes) == 2
    for i in ["2", "3"]:
        assert i in [node.uid for node in nodes]

    connected_node_repository.deregister_node("2")
    # Now, it should return node3
    nodes = connected_node_repository.get_nodes_by_model("model")
    assert len(nodes) == 1
    for i in ["3"]:
        assert i in [node.uid for node in nodes]

    connected_node_repository.deregister_node("3")
    # Now, there are no nodes left, should return None
    assert connected_node_repository.get_nodes_by_model("model") == []
    assert len(connected_node_repository._connected_nodes) == 0


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
