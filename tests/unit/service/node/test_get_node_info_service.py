from datetime import datetime
from datetime import timezone
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from uuid import UUID

from uuid_extensions import uuid7

from distributedinference.domain.node.entities import NodeInfo
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.node import get_node_info_service as service
from distributedinference.service.node.entities import GetNodeInfoResponse

NODE_UUID = UUID("40c95432-8b2c-4208-bdf4-84f49ff957a3")


async def test_execute_success():
    created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    node_info = NodeInfo(
        node_id=NODE_UUID,
        name="name",
        name_alias="name_alias",
        gpu_model="NVIDIA GTX 1080",
        vram=8,
        cpu_model="Intel i7",
        cpu_count=4,
        ram=16,
        network_download_speed=1000,
        network_upload_speed=1000,
        operating_system="Linux",
        created_at=created_at,
    )
    expected_response = GetNodeInfoResponse(
        node_id=str(NODE_UUID),
        name_alias="name_alias",
        gpu_model=node_info.gpu_model,
        vram=node_info.vram,
        cpu_model=node_info.cpu_model,
        cpu_count=node_info.cpu_count,
        ram=node_info.ram,
        network_download_speed=node_info.network_download_speed,
        network_upload_speed=node_info.network_upload_speed,
        operating_system=node_info.operating_system,
        status="online",
        run_duration_seconds=1,
        node_created_at=created_at.timestamp(),
    )

    mock_repository = AsyncMock(spec=NodeRepository)
    mock_repository.get_node_info.return_value = node_info
    mock_repository.get_connected_node_info.return_value = MagicMock(
        uid=uuid7(),
        model="model",
        connected_at=1337,
        websocket=MagicMock(),
        request_incoming_queues={},
        current_uptime=1,
    )
    response = await service.execute(node_info, mock_repository)

    assert response == expected_response


async def test_execute_success_node_offline():
    created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    node_info = NodeInfo(
        node_id=NODE_UUID,
        name="name",
        name_alias="name_alias",
        gpu_model="NVIDIA GTX 1080",
        vram=8,
        cpu_model="Intel i7",
        cpu_count=4,
        ram=16,
        network_download_speed=1000,
        network_upload_speed=1000,
        operating_system="Linux",
        created_at=created_at,
    )
    expected_response = GetNodeInfoResponse(
        node_id=str(NODE_UUID),
        name_alias="name_alias",
        gpu_model=node_info.gpu_model,
        vram=node_info.vram,
        cpu_model=node_info.cpu_model,
        cpu_count=node_info.cpu_count,
        ram=node_info.ram,
        network_download_speed=node_info.network_download_speed,
        network_upload_speed=node_info.network_upload_speed,
        operating_system=node_info.operating_system,
        status="offline",
        run_duration_seconds=0,
        node_created_at=created_at.timestamp(),
    )
    service.time = MagicMock()
    service.time.time.return_value = 1338

    mock_repository = AsyncMock(spec=NodeRepository)
    mock_repository.get_node_info.return_value = node_info
    mock_repository.get_connected_node_info.return_value = None

    response = await service.execute(node_info, mock_repository)

    assert response == expected_response
