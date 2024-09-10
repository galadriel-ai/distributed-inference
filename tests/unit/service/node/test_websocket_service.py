import json
import time
from unittest.mock import MagicMock

import pytest
from unittest.mock import AsyncMock, Mock, patch
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.exceptions import WebSocketRequestValidationError

from distributedinference.domain.node.entities import NodeBenchmark
from distributedinference.domain.node.entities import NodeMetricsIncrement
from distributedinference.domain.user.entities import User
from distributedinference.domain.node.entities import NodeMetrics
from distributedinference.repository.metrics_queue_repository import (
    MetricsQueueRepository,
)
from distributedinference.repository.node_repository import NodeRepository

from distributedinference.service.node import websocket_service


async def test_execute_node_no_model_header():
    websocket = AsyncMock(spec=WebSocket)
    user = User(uid="test_user_id", name="test_user_name", email="test_user_email")
    node_repository = AsyncMock(spec=NodeRepository)

    node_metrics = NodeMetrics()
    node_repository.get_node_metrics = AsyncMock(return_value=node_metrics)
    node_repository.register_node = Mock(return_value=False)
    node_repository.get_node_benchmark = AsyncMock(return_value=None)

    with pytest.raises(
        WebSocketRequestValidationError, match='No "Model" header provided'
    ):
        await websocket_service.execute(
            websocket, user, None, node_repository, AsyncMock()
        )

    websocket.accept.assert_called_once()
    node_repository.register_node.assert_not_called()


async def test_execute_node_no_benchmark():
    websocket = AsyncMock(spec=WebSocket)
    user = User(uid="test_user_id", name="test_user_name", email="test_user_email")
    node_repository = AsyncMock(spec=NodeRepository)

    node_metrics = NodeMetrics()
    node_repository.get_node_metrics = AsyncMock(return_value=node_metrics)
    node_repository.register_node = Mock(return_value=False)
    node_repository.get_node_benchmark = AsyncMock(return_value=None)

    with pytest.raises(
        WebSocketRequestValidationError, match="Benchmarking is not completed"
    ):
        await websocket_service.execute(
            websocket, user, "model", node_repository, AsyncMock()
        )

    websocket.accept.assert_called_once()
    node_repository.register_node.assert_not_called()


async def test_execute_node_benchmark_too_low():
    websocket = AsyncMock(spec=WebSocket)
    user = User(uid="test_user_id", name="test_user_name", email="test_user_email")
    node_repository = AsyncMock(spec=NodeRepository)

    node_metrics = NodeMetrics()
    node_repository.get_node_metrics = AsyncMock(return_value=node_metrics)
    node_repository.register_node = Mock(return_value=False)
    node_repository.get_node_benchmark = AsyncMock(
        return_value=NodeBenchmark(model_name="model", tokens_per_second=1)
    )

    with pytest.raises(
        WebSocketRequestValidationError, match="Benchmarking performance is too low"
    ):
        await websocket_service.execute(
            websocket, user, "model", node_repository, AsyncMock()
        )

    websocket.accept.assert_called_once()
    node_repository.register_node.assert_not_called()


async def test_execute_node_already_connected():
    websocket = AsyncMock(spec=WebSocket)
    user = User(uid="test_user_id", name="test_user_name", email="test_user_email")
    node_repository = AsyncMock(spec=NodeRepository)

    node_metrics = NodeMetrics()
    node_repository.get_node_metrics = AsyncMock(return_value=node_metrics)
    node_repository.register_node = Mock(return_value=False)
    node_repository.get_node_benchmark = AsyncMock(
        return_value=NodeBenchmark(model_name="model", tokens_per_second=10000)
    )

    with pytest.raises(
        WebSocketRequestValidationError,
        match="Node with same API key already connected",
    ):
        await websocket_service.execute(
            websocket, user, "model", node_repository, AsyncMock()
        )

    websocket.accept.assert_called_once()
    node_repository.register_node.assert_called_once()


async def test_execute_websocket_disconnect():
    websocket = AsyncMock(spec=WebSocket)
    websocket.receive_text = AsyncMock(side_effect=WebSocketDisconnect)

    user = User(uid="test_user_id", name="test_user_name", email="test_user_email")
    node_repository = AsyncMock(spec=NodeRepository)
    metrics_queue_repository = AsyncMock(spec=MetricsQueueRepository)

    node_repository.register_node = Mock(return_value=True)
    node_repository.get_node_benchmark = AsyncMock(
        return_value=NodeBenchmark(model_name="model", tokens_per_second=10000)
    )

    await websocket_service.execute(
        websocket, user, "model", node_repository, metrics_queue_repository
    )

    websocket.accept.assert_called_once()
    node_repository.register_node.assert_called_once()
    node_repository.deregister_node.assert_called_once_with(user.uid)
    metrics_queue_repository.push.assert_called_once()


async def test_execute_metrics_update_after_disconnect():
    websocket = AsyncMock(spec=WebSocket)
    websocket.receive_text = AsyncMock(
        side_effect=[json.dumps({"request_id": "123"}), WebSocketDisconnect()]
    )

    user = User(uid="test_user_id", name="test_user_name", email="test_user_email")
    node_repository = AsyncMock(spec=NodeRepository)

    node_repository.register_node = Mock(return_value=True)
    node_repository.save_node_metrics = AsyncMock()
    node_repository.get_node_benchmark = AsyncMock(
        return_value=NodeBenchmark(model_name="model", tokens_per_second=10000)
    )
    metrics_queue_repository = AsyncMock(spec=MetricsQueueRepository)

    start_time = time.time()

    await websocket_service.execute(
        websocket, user, "model", node_repository, metrics_queue_repository
    )

    websocket.accept.assert_called_once()
    node_repository.register_node.assert_called_once()
    node_repository.deregister_node.assert_called_once_with(user.uid)

    # This is actually just 0 most likely...
    uptime = int(time.time() - start_time)

    node_metrics = NodeMetricsIncrement(node_id="test_user_id")
    node_metrics.uptime_increment = uptime
    metrics_queue_repository.push.assert_called_once_with(node_metrics)
