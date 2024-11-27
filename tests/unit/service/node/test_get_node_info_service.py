from datetime import datetime
from datetime import timezone
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from uuid import UUID

from distributedinference.domain.node.entities import NodeInfo
from distributedinference.domain.node.entities import NodeSpecs
from distributedinference.domain.node.entities import NodeStatus
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
        created_at=created_at,
        specs=NodeSpecs(
            gpu_model="NVIDIA GTX 1080",
            vram=8,
            gpu_count=2,
            cpu_model="Intel i7",
            cpu_count=4,
            ram=16,
            power_limit=350,
            network_download_speed=1000,
            network_upload_speed=1000,
            operating_system="Linux",
            version="1337",
        ),
    )
    expected_response = GetNodeInfoResponse(
        node_id=str(NODE_UUID),
        name_alias="name_alias",
        gpu_model=node_info.specs.gpu_model,
        vram=node_info.specs.vram,
        gpu_count=node_info.specs.gpu_count,
        cpu_model=node_info.specs.cpu_model,
        cpu_count=node_info.specs.cpu_count,
        ram=node_info.specs.ram,
        network_download_speed=node_info.specs.network_download_speed,
        network_upload_speed=node_info.specs.network_upload_speed,
        operating_system=node_info.specs.operating_system,
        status="Running",
        run_duration_seconds=1,
        node_created_at=created_at.timestamp(),
        version=node_info.specs.version,
    )

    mock_repository = AsyncMock(spec=NodeRepository)
    mock_repository.get_node_metrics.return_value = MagicMock(
        requests_served=1,
        requests_successful=1,
        requests_failed=0,
        time_to_first_token=1.0,
        total_uptime=10,
        current_uptime=1,
        status=NodeStatus.RUNNING,
    )
    response = await service.execute(node_info, mock_repository)

    assert response == expected_response


async def test_execute_success_node_offline():
    created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    node_info = NodeInfo(
        node_id=NODE_UUID,
        name="name",
        name_alias="name_alias",
        created_at=created_at,
        specs=NodeSpecs(
            gpu_model="NVIDIA GTX 1080",
            vram=8,
            gpu_count=2,
            cpu_model="Intel i7",
            cpu_count=4,
            ram=16,
            power_limit=350,
            network_download_speed=1000,
            network_upload_speed=1000,
            operating_system="Linux",
        ),
    )
    expected_response = GetNodeInfoResponse(
        node_id=str(NODE_UUID),
        name_alias="name_alias",
        gpu_model=node_info.specs.gpu_model,
        vram=node_info.specs.vram,
        gpu_count=node_info.specs.gpu_count,
        cpu_model=node_info.specs.cpu_model,
        cpu_count=node_info.specs.cpu_count,
        ram=node_info.specs.ram,
        network_download_speed=node_info.specs.network_download_speed,
        network_upload_speed=node_info.specs.network_upload_speed,
        operating_system=node_info.specs.operating_system,
        status="Stopped",
        run_duration_seconds=0,
        node_created_at=created_at.timestamp(),
    )
    service.time = MagicMock()
    service.time.time.return_value = 1338

    mock_repository = AsyncMock(spec=NodeRepository)
    mock_repository.get_node_metrics.return_value = None

    response = await service.execute(node_info, mock_repository)

    assert response == expected_response


async def test_execute_missing_specs():
    created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    node_info = NodeInfo(
        node_id=NODE_UUID,
        name="name",
        name_alias="name_alias",
        created_at=created_at,
        specs=None,
    )
    expected_response = GetNodeInfoResponse(
        node_id=str(NODE_UUID),
        name_alias="name_alias",
        gpu_model=None,
        vram=None,
        gpu_count=None,
        cpu_model=None,
        cpu_count=None,
        ram=None,
        network_download_speed=None,
        network_upload_speed=None,
        operating_system=None,
        status="Running",
        run_duration_seconds=1,
        node_created_at=created_at.timestamp(),
        version=None,
    )

    mock_repository = AsyncMock(spec=NodeRepository)
    mock_repository.get_node_metrics.return_value = MagicMock(
        requests_served=1,
        requests_successful=1,
        requests_failed=0,
        time_to_first_token=1.0,
        total_uptime=10,
        current_uptime=1,
        status=NodeStatus.RUNNING,
    )
    response = await service.execute(node_info, mock_repository)

    assert response == expected_response
