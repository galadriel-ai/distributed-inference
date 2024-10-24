from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from fastapi import WebSocket

from distributedinference.domain.node.entities import NodeHealth
from distributedinference.domain.node.entities import NodeGPUHealth
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.node.protocol.health_check.entities import (
    HealthCheckMessageType,
)
from distributedinference.service.node.protocol.health_check.protocol import (
    HealthCheckProtocol,
    NodeHealthCheckInfo,
)

NODE_NAME = "test_node"
NODE_UUID = UUID("40c95432-8b2c-4208-bdf4-84f49ff957a3")
NODE_NONCE = "test_nonce"


@pytest.fixture
def node_repository():
    return AsyncMock(spec=NodeRepository)


@pytest.fixture
def health_check_protocol(node_repository):
    return HealthCheckProtocol(
        node_repository,
    )


async def test_handler_valid_response(health_check_protocol):
    # Setup
    health_check_protocol.active_nodes[NODE_NAME] = NodeHealthCheckInfo(
        websocket=AsyncMock(spec=WebSocket),
        node_uuid=NODE_UUID,
        waiting_for_response=True,
        last_request_nonce=NODE_NONCE,
    )
    data = {
        "protocol_version": HealthCheckProtocol.PROTOCOL_VERSION,
        "message_type": HealthCheckMessageType.HEALTH_CHECK_RESPONSE.value,
        "node_id": NODE_NAME,
        "nonce": NODE_NONCE,
        "cpu_percent": 50,
        "ram_percent": 50,
        "disk_percent": 50,
        "gpus": [
            {"gpu_percent": 40, "vram_percent": 30},
            {"gpu_percent": 60, "vram_percent": 20},
        ],
    }

    # Execute
    await health_check_protocol.handle(data)

    # Assert
    assert not health_check_protocol.active_nodes[NODE_NAME].waiting_for_response
    health_check_protocol.node_repository.save_node_health.assert_called_with(
        node_id=NODE_UUID,
        health=NodeHealth(
            node_id=NODE_UUID,
            cpu_percent=50,
            ram_percent=50,
            disk_percent=50,
            gpus=[
                NodeGPUHealth(gpu_percent=40, vram_percent=30),
                NodeGPUHealth(gpu_percent=60, vram_percent=20),
            ],
        ),
    )


async def test_handler_invalid_nonce(health_check_protocol):
    # Setup
    health_check_protocol.active_nodes[NODE_NAME] = NodeHealthCheckInfo(
        websocket=AsyncMock(spec=WebSocket),
        node_uuid=NODE_UUID,
        waiting_for_response=True,
        last_request_nonce="correct_nonce",
    )
    data = {
        "protocol_version": HealthCheckProtocol.PROTOCOL_VERSION,
        "message_type": HealthCheckMessageType.HEALTH_CHECK_RESPONSE.value,
        "node_id": NODE_NAME,
        "nonce": "wrong_nonce",
    }

    # Execute
    await health_check_protocol.handle(data)

    # Assert
    assert health_check_protocol.active_nodes[NODE_NAME].waiting_for_response


async def test_add_node(health_check_protocol):
    # Setup
    websocket = AsyncMock(spec=WebSocket)

    # Execute
    health_check_protocol.add_node(NODE_UUID, NODE_NAME, "0.0.15", websocket)

    # Assert
    assert NODE_NAME in health_check_protocol.active_nodes
    assert health_check_protocol.active_nodes[NODE_NAME].websocket == websocket
    assert not health_check_protocol.active_nodes[NODE_NAME].waiting_for_response


async def test_add_node_but_unsupported_node_version(health_check_protocol):
    # Setup
    websocket = AsyncMock(spec=WebSocket)

    # Execute
    health_check_protocol.add_node(NODE_UUID, NODE_NAME, "0.0.10", websocket)

    # Assert
    assert not NODE_NAME in health_check_protocol.active_nodes


async def test_remove_node(health_check_protocol):
    # Setup
    node_id = "test_node"
    health_check_protocol.active_nodes[node_id] = NodeHealthCheckInfo(
        websocket=AsyncMock(spec=WebSocket),
        node_uuid=NODE_UUID,
    )
    # Execute
    await health_check_protocol.remove_node(node_id)

    # Assert
    assert node_id not in health_check_protocol.active_nodes
