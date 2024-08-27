import pytest
from unittest.mock import MagicMock
from distributedinference.domain.node.entities import ConnectedNode
from distributedinference.repository.node_repository import NodeRepository


@pytest.fixture
def node_repository():
    return NodeRepository()


@pytest.fixture
def mock_websocket():
    return MagicMock()


@pytest.fixture
def connected_node_factory(mock_websocket):
    def _create_node(uid, model="model"):
        return ConnectedNode(uid, model, mock_websocket, MagicMock())

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
    assert selected_node == "1"


def test_select_node_after_deregistration(node_repository, connected_node_factory):
    node1 = connected_node_factory("1")
    node2 = connected_node_factory("2")
    node3 = connected_node_factory("3")

    node_repository.register_node(node1)
    node_repository.register_node(node2)
    node_repository.register_node(node3)

    # Initially, it should return node1
    assert node_repository.select_node("model") == "1"

    node_repository.deregister_node("1")
    # Now, it should return node2
    assert node_repository.select_node("model") == "2"

    node_repository.deregister_node("2")
    # Now, it should return node3
    assert node_repository.select_node("model") == "3"

    node_repository.deregister_node("3")
    # Now, there are no nodes left, should return None
    assert node_repository.select_node("model") is None
