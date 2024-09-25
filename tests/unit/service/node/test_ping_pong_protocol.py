import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import WebSocket

import settings
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.node.protocol.ping_pong_protocol import (
    PingPongProtocol,
    NodePingInfo,
)


@pytest.fixture
def node_repository():
    return AsyncMock(spec=NodeRepository)


@pytest.fixture
def ping_pong_protocol(node_repository):
    return PingPongProtocol(node_repository)


@pytest.mark.asyncio
async def test_handler_valid_pong(ping_pong_protocol):
    # Setup
    node_id = "test_node"
    nonce = "test_nonce"
    ping_pong_protocol.active_nodes[node_id] = NodePingInfo(
        websocket=AsyncMock(spec=WebSocket),
        waiting_for_pong=True,
        last_ping_nonce=nonce,
    )
    data = MagicMock(node_id=node_id, nonce=nonce)

    # Execute
    await ping_pong_protocol.handler(data)

    # Assert
    assert not ping_pong_protocol.active_nodes[node_id].waiting_for_pong
    assert ping_pong_protocol.active_nodes[node_id].ping_streak == 1
    assert ping_pong_protocol.active_nodes[node_id].miss_streak == 0


@pytest.mark.asyncio
async def test_handler_invalid_nonce(ping_pong_protocol, caplog):
    # Setup
    node_id = "test_node"
    ping_pong_protocol.active_nodes[node_id] = NodePingInfo(
        websocket=AsyncMock(spec=WebSocket),
        waiting_for_pong=True,
        last_ping_nonce="correct_nonce",
    )
    data = MagicMock(node_id=node_id, nonce="wrong_nonce")

    # Execute
    await ping_pong_protocol.handler(data)

    # Assert
    assert "Received pong with invalid nonce" in caplog.text
    assert ping_pong_protocol.active_nodes[node_id].waiting_for_pong


@pytest.mark.asyncio
async def test_job_check_for_pongs(ping_pong_protocol):
    # Setup
    current_time = round(time.time() * 1000)
    ping_pong_protocol.active_nodes = {
        "node1": NodePingInfo(
            websocket=AsyncMock(spec=WebSocket),
            waiting_for_pong=True,
            last_ping_sent_time=current_time
            - (settings.PING_TIMEOUT_IN_SECONDS * 1000)
            - 1000,
            miss_streak=0,
        ),
        "node2": NodePingInfo(
            websocket=AsyncMock(spec=WebSocket),
            waiting_for_pong=False,
            next_ping_time=(current_time - 1000),
        ),
    }

    # Execute
    await ping_pong_protocol.job()

    # Assert
    assert ping_pong_protocol.active_nodes["node1"].miss_streak == 1
    assert ping_pong_protocol.active_nodes["node2"].waiting_for_pong
    assert ping_pong_protocol.active_nodes["node2"].last_ping_sent_time >= current_time


@pytest.mark.asyncio
async def test_add_node(ping_pong_protocol):
    # Setup
    node_id = "test_node"
    websocket = AsyncMock(spec=WebSocket)

    # Execute
    ping_pong_protocol.add_node(node_id, websocket)

    # Assert
    assert node_id in ping_pong_protocol.active_nodes
    assert ping_pong_protocol.active_nodes[node_id].websocket == websocket
    assert ping_pong_protocol.active_nodes[node_id].ping_streak == 0
    assert ping_pong_protocol.active_nodes[node_id].miss_streak == 0
    assert not ping_pong_protocol.active_nodes[node_id].waiting_for_pong


@pytest.mark.asyncio
async def test_remove_node(ping_pong_protocol):
    # Setup
    node_id = "test_node"
    ping_pong_protocol.active_nodes[node_id] = NodePingInfo(
        websocket=AsyncMock(spec=WebSocket)
    )

    # Execute
    ping_pong_protocol.remove_node(node_id)

    # Assert
    assert node_id not in ping_pong_protocol.active_nodes


@pytest.mark.asyncio
async def test_got_pong_on_time(ping_pong_protocol):
    # Setup
    node_id = "test_node"
    current_time = round(time.time() * 1000)
    ping_pong_protocol.active_nodes[node_id] = NodePingInfo(
        websocket=AsyncMock(spec=WebSocket),
        waiting_for_pong=True,
        last_ping_sent_time=current_time - 500,
        ping_streak=0,
        miss_streak=1,
    )

    # Execute
    await ping_pong_protocol.got_pong_on_time(
        node_id, ping_pong_protocol.active_nodes[node_id]
    )

    # Assert
    assert not ping_pong_protocol.active_nodes[node_id].waiting_for_pong
    assert ping_pong_protocol.active_nodes[node_id].ping_streak == 1
    assert ping_pong_protocol.active_nodes[node_id].miss_streak == 0
    assert ping_pong_protocol.active_nodes[node_id].rtt > 0
