import json
import time
import uuid
from unittest.mock import AsyncMock
from unittest.mock import Mock
from uuid import UUID

import pytest
from fastapi import WebSocket
from fastapi import WebSocketDisconnect
from fastapi import status
from fastapi.exceptions import WebSocketException

from distributedinference.domain.node.entities import NodeBenchmark
from distributedinference.domain.node.entities import NodeInfo
from distributedinference.domain.node.entities import NodeMetrics
from distributedinference.domain.node.entities import NodeMetricsIncrement
from distributedinference.domain.user.entities import User
from distributedinference.repository.benchmark_repository import BenchmarkRepository
from distributedinference.repository.metrics_queue_repository import (
    MetricsQueueRepository,
)
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.node import websocket_service
from distributedinference.service.node.protocol.ping_pong_protocol import (
    PingPongProtocol,
)
from distributedinference.service.node.protocol.protocol_handler import ProtocolHandler

NODE_UUID = UUID("40c95432-8b2c-4208-bdf4-84f49ff957a3")
NODE_INFO = NodeInfo(node_id=NODE_UUID, name=str(NODE_UUID), name_alias="name_alias")


async def test_execute_node_no_model_header():
    websocket = AsyncMock(spec=WebSocket)
    user = User(uid=uuid.uuid4(), name="test_name", email="test_user_email")
    node_repository = AsyncMock(spec=NodeRepository)

    node_metrics = NodeMetrics()
    node_repository.get_node_metrics = AsyncMock(return_value=node_metrics)
    node_repository.register_node = Mock(return_value=False)

    benchmark_repository = AsyncMock(spec=BenchmarkRepository)
    benchmark_repository.get_node_benchmark = AsyncMock(return_value=None)

    with pytest.raises(
        WebSocketException, match='No "Model" header provided'
    ) as exc_info:
        await websocket_service.execute(
            websocket,
            user,
            NODE_INFO,
            None,
            node_repository,
            benchmark_repository,
            AsyncMock(),
            Mock(),
            Mock(),
        )

    assert exc_info.value.code == status.WS_1008_POLICY_VIOLATION
    websocket.accept.assert_called_once()
    node_repository.register_node.assert_not_called()


async def test_execute_node_no_benchmark():
    websocket = AsyncMock(spec=WebSocket)
    user = User(uid=uuid.uuid4(), name="test_name", email="test_user_email")
    node_repository = AsyncMock(spec=NodeRepository)

    node_metrics = NodeMetrics()
    node_repository.get_node_metrics = AsyncMock(return_value=node_metrics)
    node_repository.register_node = Mock(return_value=False)

    benchmark_repository = AsyncMock(spec=BenchmarkRepository)
    benchmark_repository.get_node_benchmark = AsyncMock(return_value=None)

    with pytest.raises(
        WebSocketException, match="Benchmarking is not completed"
    ) as exc_info:
        await websocket_service.execute(
            websocket,
            user,
            NODE_INFO,
            "model",
            node_repository,
            benchmark_repository,
            AsyncMock(),
            Mock(),
            Mock(),
        )

    assert exc_info.value.code == status.WS_1008_POLICY_VIOLATION
    websocket.accept.assert_called_once()
    node_repository.register_node.assert_not_called()


async def test_execute_node_benchmark_too_low():
    websocket = AsyncMock(spec=WebSocket)
    user = User(uid=uuid.uuid4(), name="test_name", email="test_user_email")
    node_repository = AsyncMock(spec=NodeRepository)

    node_metrics = NodeMetrics()
    node_repository.get_node_metrics = AsyncMock(return_value=node_metrics)
    node_repository.register_node = Mock(return_value=False)

    benchmark_repository = AsyncMock(spec=BenchmarkRepository)
    benchmark_repository.get_node_benchmark = AsyncMock(
        return_value=NodeBenchmark(
            node_id=NODE_UUID, model_name="model", tokens_per_second=1
        )
    )

    with pytest.raises(
        WebSocketException, match="Benchmarking performance is too low"
    ) as exc_info:
        await websocket_service.execute(
            websocket,
            user,
            NODE_INFO,
            "model",
            node_repository,
            benchmark_repository,
            AsyncMock(),
            Mock(),
            Mock(),
        )

    assert exc_info.value.code == status.WS_1008_POLICY_VIOLATION
    websocket.accept.assert_called_once()
    node_repository.register_node.assert_not_called()


async def test_execute_node_already_connected():
    websocket = AsyncMock(spec=WebSocket)
    user = User(uid=uuid.uuid4(), name="test_name", email="test_user_email")
    node_repository = AsyncMock(spec=NodeRepository)

    node_metrics = NodeMetrics()
    node_repository.get_node_metrics = AsyncMock(return_value=node_metrics)
    node_repository.register_node = Mock(return_value=False)

    benchmark_repository = AsyncMock(spec=BenchmarkRepository)
    benchmark_repository.get_node_benchmark = AsyncMock(
        return_value=NodeBenchmark(
            node_id=NODE_UUID, model_name="model", tokens_per_second=10000
        )
    )

    with pytest.raises(
        WebSocketException,
        match="Node with same node id already connected",
    ) as exc_info:
        await websocket_service.execute(
            websocket,
            user,
            NODE_INFO,
            "model",
            node_repository,
            benchmark_repository,
            AsyncMock(),
            Mock(),
            Mock(),
        )

    assert exc_info.value.code == status.WS_1008_POLICY_VIOLATION
    websocket.accept.assert_called_once()
    node_repository.register_node.assert_called_once()


async def test_execute_websocket_disconnect():
    websocket = AsyncMock(spec=WebSocket)
    websocket.receive_text = AsyncMock(side_effect=WebSocketDisconnect)

    user = User(uid=uuid.uuid4(), name="test_name", email="test_user_email")
    node_repository = AsyncMock(spec=NodeRepository)
    metrics_queue_repository = AsyncMock(spec=MetricsQueueRepository)

    node_repository.register_node = Mock(return_value=True)

    benchmark_repository = AsyncMock(spec=BenchmarkRepository)
    benchmark_repository.get_node_benchmark = AsyncMock(
        return_value=NodeBenchmark(
            node_id=NODE_UUID, model_name="model", tokens_per_second=10000
        )
    )

    await websocket_service.execute(
        websocket,
        user,
        NODE_INFO,
        "model",
        node_repository,
        benchmark_repository,
        metrics_queue_repository,
        AsyncMock(),
        Mock(),
    )

    # Assert
    websocket.accept.assert_called_once()
    node_repository.register_node.assert_called_once()
    node_repository.deregister_node.assert_called_once_with(NODE_UUID)
    metrics_queue_repository.push.assert_called_once()


async def test_execute_metrics_update_after_disconnect():
    websocket = AsyncMock(spec=WebSocket)
    websocket.receive_text = AsyncMock(
        side_effect=[json.dumps({"request_id": "123"}), WebSocketDisconnect()]
    )

    user = User(uid=uuid.uuid4(), name="test_name", email="test_user_email")
    node_repository = AsyncMock(spec=NodeRepository)

    node_repository.register_node = Mock(return_value=True)
    node_repository.increment_node_metrics = AsyncMock()

    benchmark_repository = AsyncMock(spec=BenchmarkRepository)
    benchmark_repository.get_node_benchmark = AsyncMock(
        return_value=NodeBenchmark(
            node_id=NODE_UUID, model_name="model", tokens_per_second=10000
        )
    )
    metrics_queue_repository = AsyncMock(spec=MetricsQueueRepository)

    start_time = time.time()

    await websocket_service.execute(
        websocket,
        user,
        NODE_INFO,
        "model",
        node_repository,
        benchmark_repository,
        metrics_queue_repository,
        Mock(),
        Mock(),
    )

    node_repository.register_node.assert_called_once()
    node_repository.deregister_node.assert_called_once_with(NODE_UUID)
    # This is actually just 0 most likely...
    uptime = int(time.time() - start_time)

    node_metrics = NodeMetricsIncrement(node_id=NODE_UUID)
    node_metrics.uptime_increment = uptime
    metrics_queue_repository.push.assert_called_once_with(node_metrics)


@pytest.mark.asyncio
async def test_execute_ping_pong_protocol():
    websocket = AsyncMock(spec=WebSocket)
    websocket.receive_text = AsyncMock(side_effect=WebSocketDisconnect)

    user = User(uid=uuid.uuid4(), name="test_name", email="test_user_email")
    node_repository = AsyncMock(spec=NodeRepository)
    metrics_queue_repository = AsyncMock(spec=MetricsQueueRepository)
    node_repository.get_node_benchmark = AsyncMock(return_value=None)
    ping_pong_protocol = AsyncMock(spec=PingPongProtocol)
    protocol_handler = AsyncMock(spec=ProtocolHandler)
    protocol_handler.get = Mock(return_value=ping_pong_protocol)

    node_repository.register_node = Mock(return_value=True)
    node_repository.get_node_benchmark = AsyncMock(
        return_value=NodeBenchmark(
            node_id=NODE_UUID, model_name="model", tokens_per_second=10000
        )
    )

    await websocket_service.execute(
        websocket,
        user,
        NODE_INFO,
        "model",
        node_repository,
        metrics_queue_repository,
        Mock(),
        protocol_handler,
    )

    # Check if add_node was called
    ping_pong_protocol.add_node.assert_called_once_with(str(NODE_UUID), websocket)

    # Check if remove_node was called
    ping_pong_protocol.remove_node.assert_called_once_with(str(NODE_UUID))

    # Verify other expected method calls
    websocket.accept.assert_called_once()
    node_repository.register_node.assert_called_once()
    node_repository.deregister_node.assert_called_once_with(NODE_UUID)
