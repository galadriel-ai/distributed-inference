import uuid
from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import Mock
from uuid import UUID

import pytest
from fastapi import WebSocket
from fastapi import WebSocketDisconnect
from fastapi import status
from fastapi.exceptions import WebSocketException

import settings
from distributedinference.domain.node.entities import FullNodeInfo
from distributedinference.domain.node.entities import NodeBenchmark
from distributedinference.domain.node.entities import NodeMetrics
from distributedinference.domain.node.entities import NodeSpecs
from distributedinference.domain.node.entities import NodeStatus
from distributedinference.domain.user.entities import User
from distributedinference.repository.benchmark_repository import BenchmarkRepository
from distributedinference.repository.connected_node_repository import (
    ConnectedNodeRepository,
)
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.node import websocket_service
from distributedinference.service.node.protocol.ping_pong_protocol import (
    PingPongProtocol,
)
from distributedinference.service.node.protocol.protocol_handler import ProtocolHandler


def _get_node_specs() -> NodeSpecs:
    return NodeSpecs(
        cpu_model="mock_cpu_model",
        cpu_count=1,
        gpu_model="mock_gpu_model",
        vram=2,
        ram=3,
        power_limit=350,
        network_download_speed=100,
        network_upload_speed=50,
        operating_system="mock_operating_system",
        gpu_count=1,
        version="0.0.1",
    )


NODE_UUID = UUID("40c95432-8b2c-4208-bdf4-84f49ff957a3")
NODE_INFO = FullNodeInfo(
    node_id=NODE_UUID,
    name=str(NODE_UUID),
    name_alias="name_alias",
    created_at=datetime(2024, 1, 5),
    specs=_get_node_specs(),
)


@pytest.fixture
def node_repository() -> AsyncMock(spec=NodeRepository):
    node_repository = AsyncMock(spec=NodeRepository)
    node_repository.get_node_metrics_by_ids = AsyncMock(return_value={})
    node_repository.get_node_status = AsyncMock(return_value=NodeStatus.RUNNING)
    return node_repository


@pytest.fixture
def connected_node_repository() -> AsyncMock(spec=ConnectedNodeRepository):
    repository = AsyncMock(spec=ConnectedNodeRepository)
    repository.register_node = Mock(return_value=True)
    return repository


async def test_execute_node_no_model_header(
    node_repository: AsyncMock,
    connected_node_repository: AsyncMock,
):
    websocket = AsyncMock(spec=WebSocket)
    user = User(
        uid=uuid.uuid4(),
        name="test_name",
        email="test_user_email",
        usage_tier_id=UUID("06706644-2409-7efd-8000-3371c5d632d3"),
    )

    node_metrics = NodeMetrics(status=NodeStatus.STOPPED)
    node_repository.get_node_metrics_by_ids = AsyncMock(
        return_value={NODE_UUID: node_metrics}
    )
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
            None,
            node_repository,
            connected_node_repository,
            benchmark_repository,
            Mock(),
            Mock(),
        )

    assert exc_info.value.code == status.WS_1008_POLICY_VIOLATION
    websocket.accept.assert_called_once()
    connected_node_repository.register_node.assert_not_called()
    node_repository.set_node_connection_timestamp.assert_not_called()


async def test_execute_node_no_benchmark(
    node_repository: AsyncMock,
    connected_node_repository: AsyncMock,
):
    websocket = AsyncMock(spec=WebSocket)
    user = User(
        uid=uuid.uuid4(),
        name="test_name",
        email="test_user_email",
        usage_tier_id=UUID("06706644-2409-7efd-8000-3371c5d632d3"),
    )

    node_metrics = NodeMetrics(status=NodeStatus.STOPPED)
    node_repository.get_node_metrics_by_ids = AsyncMock(
        return_value={NODE_UUID: node_metrics}
    )
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
            None,
            node_repository,
            connected_node_repository,
            benchmark_repository,
            Mock(),
            Mock(),
        )

    assert exc_info.value.code == status.WS_1008_POLICY_VIOLATION
    websocket.accept.assert_called_once()
    connected_node_repository.register_node.assert_not_called()
    node_repository.set_node_connection_timestamp.assert_not_called()


async def test_execute_node_benchmark_too_low(
    node_repository: AsyncMock,
    connected_node_repository: AsyncMock,
):
    websocket = AsyncMock(spec=WebSocket)
    user = User(
        uid=uuid.uuid4(),
        name="test_name",
        email="test_user_email",
        usage_tier_id=UUID("06706644-2409-7efd-8000-3371c5d632d3"),
    )

    node_metrics = NodeMetrics(status=NodeStatus.STOPPED)
    node_repository.get_node_metrics_by_ids = AsyncMock(
        return_value={NODE_UUID: node_metrics}
    )
    node_repository.register_node = Mock(return_value=False)

    benchmark_repository = AsyncMock(spec=BenchmarkRepository)
    benchmark_repository.get_node_benchmark = AsyncMock(
        return_value=NodeBenchmark(
            node_id=NODE_UUID,
            model_name="model",
            benchmark_tokens_per_second=1,
            gpu_model="NVIDIA GeForce RTX 4090",
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
            None,
            node_repository,
            connected_node_repository,
            benchmark_repository,
            Mock(),
            Mock(),
        )

    assert exc_info.value.code == status.WS_1008_POLICY_VIOLATION
    websocket.accept.assert_called_once()
    connected_node_repository.register_node.assert_not_called()
    node_repository.set_node_connection_timestamp.assert_not_called()


async def test_execute_node_benchmark_405b_enough(
    node_repository: AsyncMock,
    connected_node_repository: AsyncMock,
):
    websocket = AsyncMock(spec=WebSocket)
    user = User(
        uid=uuid.uuid4(),
        name="test_name",
        email="test_user_email",
        usage_tier_id=UUID("06706644-2409-7efd-8000-3371c5d632d3"),
    )

    node_metrics = NodeMetrics(status=NodeStatus.STOPPED)
    node_repository.get_node_metrics_by_ids = AsyncMock(
        return_value={NODE_UUID: node_metrics}
    )
    connected_node_repository.register_node = Mock(return_value=False)

    model_name = next(iter(settings.MINIMUM_COMPLETIONS_TOKENS_PER_SECOND_PER_MODEL))
    benchmark_repository = AsyncMock(spec=BenchmarkRepository)
    benchmark_repository.get_node_benchmark = AsyncMock(
        return_value=NodeBenchmark(
            node_id=NODE_UUID,
            model_name="model_name",
            benchmark_tokens_per_second=settings.MINIMUM_COMPLETIONS_TOKENS_PER_SECOND_PER_MODEL[
                model_name
            ]
            + 1,
            gpu_model="NVIDIA GeForce RTX 4090",
        )
    )

    with pytest.raises(
        # Passes benchmark check, gets next error
        WebSocketException,
        match="Node with same node id already connected",
    ) as exc_info:
        await websocket_service.execute(
            websocket,
            user,
            NODE_INFO,
            model_name,
            None,
            node_repository,
            connected_node_repository,
            benchmark_repository,
            Mock(),
            Mock(),
        )

    assert exc_info.value.code == status.WS_1008_POLICY_VIOLATION
    websocket.accept.assert_called_once()
    connected_node_repository.register_node.assert_called_once()
    node_repository.set_node_connection_timestamp.assert_called_once()


async def test_node_already_connected_with_other_worker(
    node_repository: AsyncMock,
    connected_node_repository: AsyncMock,
):
    websocket = AsyncMock(spec=WebSocket)
    user = User(
        uid=uuid.uuid4(),
        name="test_name",
        email="test_user_email",
        usage_tier_id=UUID("06706644-2409-7efd-8000-3371c5d632d3"),
    )
    node_info = FullNodeInfo(
        node_id=NODE_UUID,
        name=str(NODE_UUID),
        name_alias="name_alias",
        created_at=datetime(2024, 1, 5),
        specs=_get_node_specs(),
    )

    node_metrics = NodeMetrics(status=NodeStatus.RUNNING, is_active=True)
    node_repository.get_node_metrics_by_ids = AsyncMock(
        return_value={NODE_UUID: node_metrics}
    )
    connected_node_repository.register_node = Mock(return_value=False)

    benchmark_repository = AsyncMock(spec=BenchmarkRepository)
    benchmark_repository.get_node_benchmark = AsyncMock(
        return_value=NodeBenchmark(
            node_id=NODE_UUID,
            model_name="model",
            benchmark_tokens_per_second=10000,
            gpu_model="NVIDIA GeForce RTX 4090",
        )
    )

    with pytest.raises(
        WebSocketException,
        match="A existing connection has already been established",
    ) as exc_info:
        await websocket_service.execute(
            websocket,
            user,
            node_info,
            "model",
            None,
            node_repository,
            connected_node_repository,
            benchmark_repository,
            Mock(),
            Mock(),
        )

    assert exc_info.value.code == status.WS_1008_POLICY_VIOLATION
    websocket.accept.assert_called_once()
    connected_node_repository.register_node.assert_not_called()
    node_repository.set_node_connection_timestamp.assert_not_called()


async def test_execute_node_already_connected(
    node_repository: AsyncMock,
    connected_node_repository: AsyncMock,
):
    websocket = AsyncMock(spec=WebSocket)
    user = User(
        uid=uuid.uuid4(),
        name="test_name",
        email="test_user_email",
        usage_tier_id=UUID("06706644-2409-7efd-8000-3371c5d632d3"),
    )

    node_metrics = NodeMetrics(status=NodeStatus.STOPPED)
    node_repository.get_node_metrics_by_ids = AsyncMock(
        return_value={NODE_UUID: node_metrics}
    )
    connected_node_repository.register_node = Mock(return_value=False)

    benchmark_repository = AsyncMock(spec=BenchmarkRepository)
    benchmark_repository.get_node_benchmark = AsyncMock(
        return_value=NodeBenchmark(
            node_id=NODE_UUID,
            model_name="model",
            benchmark_tokens_per_second=10000,
            gpu_model="NVIDIA GeForce RTX 4090",
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
            None,
            node_repository,
            connected_node_repository,
            benchmark_repository,
            Mock(),
            Mock(),
        )

    assert exc_info.value.code == status.WS_1008_POLICY_VIOLATION
    websocket.accept.assert_called_once()
    connected_node_repository.register_node.assert_called_once()


async def test_execute_websocket_disconnect(
    node_repository: AsyncMock, connected_node_repository: AsyncMock
):
    websocket = AsyncMock(spec=WebSocket)
    websocket.receive_text = AsyncMock(side_effect=WebSocketDisconnect)

    ping_pong_protocol = AsyncMock(spec=PingPongProtocol)
    ping_pong_protocol.add_node = Mock()
    ping_pong_protocol.remove_node = AsyncMock()
    protocol_handler = AsyncMock(spec=ProtocolHandler)
    protocol_handler.get = Mock(return_value=ping_pong_protocol)

    user = User(
        uid=uuid.uuid4(),
        name="test_name",
        email="test_user_email",
        usage_tier_id=UUID("06706644-2409-7efd-8000-3371c5d632d3"),
    )

    benchmark_repository = AsyncMock(spec=BenchmarkRepository)
    benchmark_repository.get_node_benchmark = AsyncMock(
        return_value=NodeBenchmark(
            node_id=NODE_UUID,
            model_name="model",
            benchmark_tokens_per_second=10000,
            gpu_model="NVIDIA GeForce RTX 4090",
        )
    )

    await websocket_service.execute(
        websocket,
        user,
        NODE_INFO,
        "model",
        None,
        node_repository,
        connected_node_repository,
        benchmark_repository,
        Mock(),
        protocol_handler,
    )

    # Assert
    websocket.accept.assert_called_once()
    connected_node_repository.register_node.assert_called_once()
    connected_node_repository.deregister_node.assert_called_once_with(NODE_UUID)
    node_repository.set_node_connection_timestamp.assert_called_once()
    node_repository.update_node_to_disconnected.assert_called_once_with(
        NODE_UUID, NodeStatus.STOPPED
    )


async def test_execute_protocols(
    node_repository: AsyncMock,
    connected_node_repository: AsyncMock,
):
    websocket = AsyncMock(spec=WebSocket)
    websocket.receive_text = AsyncMock(side_effect=WebSocketDisconnect)

    user = User(
        uid=uuid.uuid4(),
        name="test_name",
        email="test_user_email",
        usage_tier_id=UUID("06706644-2409-7efd-8000-3371c5d632d3"),
    )
    ping_pong_protocol = AsyncMock(spec=PingPongProtocol)
    ping_pong_protocol.add_node = Mock()
    ping_pong_protocol.remove_node = AsyncMock()
    health_check_protocol = AsyncMock(spec=PingPongProtocol)
    health_check_protocol.add_node = Mock()
    health_check_protocol.remove_node = AsyncMock()
    protocol_handler = AsyncMock(spec=ProtocolHandler)
    protocol_handler.get = Mock(side_effect=[ping_pong_protocol, health_check_protocol])

    connected_node_repository.register_node = Mock(return_value=True)
    node_repository.get_node_benchmark = AsyncMock(
        return_value=NodeBenchmark(
            node_id=NODE_UUID,
            model_name="model",
            benchmark_tokens_per_second=10000,
            gpu_model="NVIDIA GeForce RTX 4090",
        )
    )

    benchmark_repository = AsyncMock(spec=BenchmarkRepository)
    benchmark_repository.get_node_benchmark = AsyncMock(
        return_value=NodeBenchmark(
            node_id=NODE_UUID,
            model_name="model",
            benchmark_tokens_per_second=10000,
            gpu_model="NVIDIA GeForce RTX 4090",
        )
    )

    await websocket_service.execute(
        websocket,
        user,
        NODE_INFO,
        "model",
        None,
        node_repository,
        connected_node_repository,
        benchmark_repository,
        Mock(),
        protocol_handler,
    )

    # Check if add_node was called
    ping_pong_protocol.add_node.assert_called_once_with(
        NODE_UUID, str(NODE_UUID), "model"
    )

    # Check if remove_node was called
    ping_pong_protocol.remove_node.assert_called_once_with(str(NODE_UUID))

    # Check if add_node was called
    health_check_protocol.add_node.assert_called_once_with(
        NODE_UUID, str(NODE_UUID), NODE_INFO.specs.version
    )

    # Check if remove_node was called
    health_check_protocol.remove_node.assert_called_once_with(str(NODE_UUID))

    # Verify other expected method calls
    websocket.accept.assert_called_once()
    connected_node_repository.register_node.assert_called_once()
    connected_node_repository.deregister_node.assert_called_once_with(NODE_UUID)
    node_repository.set_node_connection_timestamp.assert_called_once()
    node_repository.update_node_to_disconnected.assert_called_once_with(
        NODE_UUID, NodeStatus.STOPPED
    )


async def test_execute_node_image_generation_model(
    node_repository: AsyncMock,
    connected_node_repository: AsyncMock,
):
    websocket = AsyncMock(spec=WebSocket)
    websocket.receive_text = AsyncMock()

    user = User(
        uid=uuid.uuid4(),
        name="test_name",
        email="test_user_email",
        usage_tier_id=UUID("06706644-2409-7efd-8000-3371c5d632d3"),
    )

    node_metrics = NodeMetrics(status=NodeStatus.STOPPED)
    node_repository.get_node_metrics_by_ids = AsyncMock(
        return_value={NODE_UUID: node_metrics}
    )
    connected_node_repository.register_node = Mock(return_value=True)

    ping_pong_protocol = AsyncMock(spec=PingPongProtocol)
    ping_pong_protocol.add_node = Mock()
    ping_pong_protocol.remove_node = AsyncMock()
    health_check_protocol = AsyncMock(spec=PingPongProtocol)
    health_check_protocol.add_node = Mock()
    health_check_protocol.remove_node = AsyncMock()
    protocol_handler = AsyncMock(spec=ProtocolHandler)
    protocol_handler.get = Mock(side_effect=[ping_pong_protocol, health_check_protocol])

    benchmark_repository = AsyncMock(spec=BenchmarkRepository)
    benchmark_repository.get_node_benchmark = AsyncMock(
        return_value=NodeBenchmark(
            node_id=NODE_UUID,
            model_name="model",
            benchmark_tokens_per_second=10000,
            gpu_model="NVIDIA GeForce RTX 4090",
        )
    )

    await websocket_service.execute(
        websocket,
        user,
        NODE_INFO,
        "model",
        "DIFFUSION",
        node_repository,
        connected_node_repository,
        benchmark_repository,
        Mock(),
        protocol_handler,
    )

    websocket.accept.assert_called_once()
    connected_node_repository.register_node.assert_called_once()
    node_repository.set_node_connection_timestamp.assert_called_once()
    ping_pong_protocol.add_node.assert_called_once()
    health_check_protocol.add_node.assert_not_called()
