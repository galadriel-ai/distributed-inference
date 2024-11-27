from datetime import datetime
from unittest.mock import AsyncMock
from uuid import UUID

from uuid_extensions import uuid7

from distributedinference.domain.node.entities import FullNodeInfo
from distributedinference.domain.node.entities import NodeInfo
from distributedinference.domain.node.entities import NodeSpecs
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.node import save_node_info_service as service
from distributedinference.service.node.entities import PostNodeInfoRequest
from distributedinference.service.node.entities import PostNodeInfoResponse

NODE_UUID = UUID("40c95432-8b2c-4208-bdf4-84f49ff957a3")


async def test_execute_success():
    node_id = uuid7()
    request = PostNodeInfoRequest(
        node_id=str(NODE_UUID),
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
        version="0.10.0",
    )

    expected_node_info = FullNodeInfo(
        node_id=NODE_UUID,
        name="name",
        name_alias="name_alias",
        created_at=datetime(2020, 1, 1),
        specs=NodeSpecs(
            gpu_model=request.gpu_model,
            vram=request.vram,
            gpu_count=request.gpu_count,
            cpu_model=request.cpu_model,
            cpu_count=request.cpu_count,
            ram=request.ram,
            power_limit=request.power_limit,
            network_download_speed=request.network_download_speed,
            network_upload_speed=request.network_upload_speed,
            operating_system=request.operating_system,
            version=request.version,
        ),
    )

    mock_repository = AsyncMock(spec=NodeRepository)
    response = await service.execute(
        request,
        NodeInfo(
            node_id=NODE_UUID,
            name="name",
            name_alias="name_alias",
            created_at=datetime(2020, 1, 1),
            specs=None,
        ),
        node_id,
        mock_repository,
    )
    mock_repository.save_node_info.assert_called_once_with(node_id, expected_node_info)

    assert response == PostNodeInfoResponse(response="OK")
