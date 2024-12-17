import time
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from uuid import UUID
from uuid import uuid1

import pytest
from uuid_extensions import uuid7

from distributedinference.domain.node.entities import BackendHost
from distributedinference.domain.node.entities import ConnectedNode
from distributedinference.domain.node.entities import ModelType
from distributedinference.domain.node.entities import NodeMetricsIncrement
from distributedinference.domain.node.entities import NodeStatus
from distributedinference.repository.connection import DBConnection
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.node_repository import (
    SQL_INCREMENT_NODE_METRICS,
)

MAX_PARALLEL_REQUESTS = 10
MAX_PARALLEL_DATACENTER_REQUESTS = 20
NODE_UUID = UUID("40c95432-8b2c-4208-bdf4-84f49ff957a3")


@pytest.fixture
def session_provider():
    mock_session_provider = MagicMock(spec=DBConnection)
    return mock_session_provider


@pytest.fixture
def node_repository(session_provider):
    return NodeRepository(
        session_provider,
        session_provider,
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
            BackendHost.DISTRIBUTED_INFERENCE_EU,
            mock_websocket,
            {},
            node_status,
            ModelType.LLM,
            is_self_hosted,
            None,
        )

    return _create_node


async def test_save_node_metrics(node_repository, session_provider):
    node_id = uuid7()

    node_metrics = NodeMetricsIncrement(
        node_id=node_id,
        model="model",
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
    assert data["node_info_id"] == node_id
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
    assert "last_updated_at" in data

    # Check if the commit was called
    mock_session.commit.assert_called_once()
