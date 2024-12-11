import time
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

import settings
from distributedinference.domain.node.entities import NodeMetricsIncrement
from distributedinference.repository.connected_node_repository import (
    ConnectedNodeRepository,
)
from distributedinference.repository.metrics_queue_repository import (
    MetricsQueueRepository,
)
from distributedinference.service.node.protocol.ping_pong_protocol import NodePingInfo
from distributedinference.service.node.protocol.ping_pong_protocol import (
    PingPongProtocol,
)

NODE_NAME = "test_node"
NODE_UUID = UUID("40c95432-8b2c-4208-bdf4-84f49ff957a3")
NODE_NONCE = "test_nonce"


@pytest.fixture
def metrics_queue_repository():
    return AsyncMock(spec=MetricsQueueRepository)


@pytest.fixture
def connected_node_repository():
    return AsyncMock(spec=ConnectedNodeRepository)


@pytest.fixture
def ping_pong_protocol(metrics_queue_repository, connected_node_repository):
    return PingPongProtocol(
        metrics_queue_repository,
        connected_node_repository,
        settings.PING_PONG_PROTOCOL_NAME,
        settings.GALADRIEL_PROTOCOL_CONFIG[settings.PING_PONG_PROTOCOL_NAME],
    )


@pytest.mark.asyncio
async def test_handler_valid_pong(ping_pong_protocol):
    # Setup
    _update_rtt = AsyncMock()
    ping_pong_protocol.active_nodes[NODE_NAME] = NodePingInfo(
        node_uuid=NODE_UUID,
        model="model",
        waiting_for_pong=True,
        ping_nonce=NODE_NONCE,
    )
    data = {
        "protocol_version": ping_pong_protocol.config.version,
        "message_type": 2,  # Pong message type
        "node_id": NODE_NAME,
        "nonce": NODE_NONCE,
        "api_ping_time": [10, 20],
    }

    # Execute
    await ping_pong_protocol.handle(data)

    # Assert
    assert not ping_pong_protocol.active_nodes[NODE_NAME].waiting_for_pong
    assert ping_pong_protocol.active_nodes[NODE_NAME].ping_streak == 1
    assert ping_pong_protocol.active_nodes[NODE_NAME].miss_streak == 0


@pytest.mark.asyncio
async def test_handler_invalid_nonce(ping_pong_protocol, caplog):
    # Setup
    ping_pong_protocol.active_nodes[NODE_NAME] = NodePingInfo(
        node_uuid=NODE_UUID,
        model="model",
        waiting_for_pong=True,
        ping_nonce="correct_nonce",
    )
    data = {
        "protocol_version": ping_pong_protocol.config.version,
        "message_type": 2,  # Pong message type
        "node_id": NODE_NAME,
        "nonce": "wrong_nonce",
        "api_ping_time": [10, 20],
    }

    # Execute
    await ping_pong_protocol.handle(data)

    # Assert
    assert ping_pong_protocol.active_nodes[NODE_NAME].waiting_for_pong


@pytest.mark.asyncio
async def test_handler_invalid_api_ping_time(ping_pong_protocol):
    # Setup
    ping_pong_protocol.active_nodes[NODE_NAME] = NodePingInfo(
        node_uuid=NODE_UUID,
        model="model",
        waiting_for_pong=True,
        ping_nonce="correct_nonce",
    )
    data = {
        "protocol_version": ping_pong_protocol.config.version,
        "message_type": 2,  # Pong message type
        "node_id": NODE_NAME,
        "nonce": "wrong_nonce",
        "api_ping_time": [],
    }

    # Execute
    await ping_pong_protocol.handle(data)

    # Assert
    assert ping_pong_protocol.active_nodes[NODE_NAME].waiting_for_pong


@pytest.mark.asyncio
async def test_handler_send_reconnect_request(ping_pong_protocol):
    # Setup
    ping_pong_protocol._send_node_reconnect_request = AsyncMock()
    current_time = time.time_ns() // 1_000_000
    ping_pong_protocol.active_nodes[NODE_NAME] = NodePingInfo(
        node_uuid=NODE_UUID,
        model="model",
        waiting_for_pong=True,
        ping_sent_time=current_time - 200,
        ping_nonce=NODE_NONCE,
    )
    data = {
        "protocol_version": ping_pong_protocol.config.version,
        "message_type": 2,  # Pong message type
        "node_id": NODE_NAME,
        "nonce": NODE_NONCE,
        "api_ping_time": [10, 20],
    }

    # Execute
    await ping_pong_protocol.handle(data)

    # Assert
    ping_pong_protocol._send_node_reconnect_request.assert_called_once()


@pytest.mark.asyncio
async def test_handler_not_sent_reconnect_request_because_api_ping_too_many_none(
    ping_pong_protocol,
):
    # Setup
    ping_pong_protocol._send_node_reconnect_request = AsyncMock()
    current_time = time.time_ns() // 1_000_000
    ping_pong_protocol.active_nodes[NODE_NAME] = NodePingInfo(
        node_uuid=NODE_UUID,
        model="model",
        waiting_for_pong=True,
        ping_sent_time=current_time - 200,
        ping_nonce=NODE_NONCE,
    )
    data = {
        "protocol_version": ping_pong_protocol.config.version,
        "message_type": 2,  # Pong message type
        "node_id": NODE_NAME,
        "nonce": NODE_NONCE,
        "api_ping_time": [None, None, 20],  # more than 50% of None
    }

    # Execute
    await ping_pong_protocol.handle(data)

    # Assert
    ping_pong_protocol._send_node_reconnect_request.assert_not_called()


@pytest.mark.asyncio
async def test_handler_not_sent_reconnect_request_because_api_ping_too_high(
    ping_pong_protocol,
):
    # Setup
    ping_pong_protocol._send_node_reconnect_request = AsyncMock()
    current_time = time.time_ns() // 1000000
    ping_pong_protocol.active_nodes[NODE_NAME] = NodePingInfo(
        node_uuid=NODE_UUID,
        model="model",
        waiting_for_pong=True,
        ping_sent_time=current_time - 200,
        ping_nonce=NODE_NONCE,
    )
    data = {
        "protocol_version": ping_pong_protocol.config.version,
        "message_type": 2,  # Pong message type
        "node_id": NODE_NAME,
        "nonce": NODE_NONCE,
        "api_ping_time": [
            10,
            130,
            20,
        ],  # at least one ping time is higher than the threshold
    }

    # Execute
    await ping_pong_protocol.handle(data)

    # Assert
    ping_pong_protocol._send_node_reconnect_request.assert_not_called()


@pytest.mark.asyncio
async def test_job_check_for_pongs(ping_pong_protocol):
    # Setup
    current_time = time.time_ns() // 1_000_000
    ping_pong_protocol.active_nodes = {
        "node1": NodePingInfo(
            node_uuid=NODE_UUID,
            model="model",
            waiting_for_pong=True,
            ping_sent_time=current_time
            - ping_pong_protocol.config.ping_timeout_in_msec
            - 1000,
            miss_streak=0,
        ),
        "node2": NodePingInfo(
            node_uuid=UUID("40c95432-8b2c-4208-bdf4-84f49ff957a4"),
            model="model",
            waiting_for_pong=False,
            next_ping_time=(current_time - 1000),
        ),
    }

    # Execute
    await ping_pong_protocol.run()

    # Assert
    assert ping_pong_protocol.active_nodes["node1"].miss_streak == 1
    assert ping_pong_protocol.active_nodes["node2"].waiting_for_pong
    assert ping_pong_protocol.active_nodes["node2"].ping_sent_time >= current_time
    assert ping_pong_protocol.active_nodes["node2"].model == "model"


@pytest.mark.asyncio
async def test_add_node(ping_pong_protocol):
    ping_pong_protocol.add_node(NODE_UUID, NODE_NAME, "model")
    assert NODE_NAME in ping_pong_protocol.active_nodes
    assert ping_pong_protocol.active_nodes[NODE_NAME].ping_streak == 0
    assert ping_pong_protocol.active_nodes[NODE_NAME].miss_streak == 0
    assert ping_pong_protocol.active_nodes[NODE_NAME].model == "model"
    assert not ping_pong_protocol.active_nodes[NODE_NAME].waiting_for_pong


@pytest.mark.asyncio
async def test_remove_node(ping_pong_protocol):
    # Setup
    node_id = "test_node"
    ping_pong_protocol.active_nodes[node_id] = NodePingInfo(
        node_uuid=NODE_UUID,
        model="model",
    )
    metrics_queue_repository = AsyncMock(spec=MetricsQueueRepository)

    # Execute
    await ping_pong_protocol.remove_node(node_id)

    # Assert
    assert node_id not in ping_pong_protocol.active_nodes
    ping_pong_protocol.metrics_queue_repository.push.assert_called_once()


@pytest.mark.asyncio
async def test_got_pong_on_time(ping_pong_protocol):
    # Setup
    node_id = "test_node"
    current_time = time.time_ns() // 1_000_000
    ping_pong_protocol.active_nodes[node_id] = NodePingInfo(
        node_uuid=NODE_UUID,
        model="model",
        waiting_for_pong=True,
        ping_sent_time=current_time - 500,
        ping_streak=0,
        miss_streak=1,
    )
    metrics_queue_repository = AsyncMock(spec=MetricsQueueRepository)

    # Execute
    await ping_pong_protocol.got_pong_on_time(
        node_id, ping_pong_protocol.active_nodes[node_id], (current_time - 100)
    )

    # Assert
    assert not ping_pong_protocol.active_nodes[node_id].waiting_for_pong
    assert ping_pong_protocol.active_nodes[node_id].ping_streak == 1
    assert ping_pong_protocol.active_nodes[node_id].miss_streak == 0
    assert ping_pong_protocol.active_nodes[node_id].rtt > 0
    ping_pong_protocol.metrics_queue_repository.push.assert_called_once()


@pytest.mark.asyncio
async def test_execute_metrics_update_when_removing_node(ping_pong_protocol):
    # Setup
    node_id = "test_node"
    ping_pong_protocol.active_nodes[node_id] = NodePingInfo(
        node_uuid=NODE_UUID,
        model="model",
        last_uptime_update_time_in_seconds=time.time() - 10,
    )

    # Execute
    await ping_pong_protocol.remove_node(node_id)

    # Assert
    assert node_id not in ping_pong_protocol.active_nodes

    node_metrics = NodeMetricsIncrement(node_id=NODE_UUID, model="model")
    # It should be roughly 10 as the time is in seconds
    node_metrics.uptime_increment = 10
    ping_pong_protocol.metrics_queue_repository.push.assert_called_once_with(
        node_metrics
    )
