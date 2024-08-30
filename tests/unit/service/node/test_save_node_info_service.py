from unittest.mock import AsyncMock

from uuid_extensions import uuid7

from distributedinference.domain.node.entities import NodeInfo
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.node import save_node_info_service as service
from distributedinference.service.node.entities import PostNodeInfoRequest
from distributedinference.service.node.entities import PostNodeInfoResponse


async def test_execute_success():
    node_id = uuid7()
    request = PostNodeInfoRequest(
        gpu_model="NVIDIA GTX 1080",
        vram=8,
        cpu_model="Intel i7",
        cpu_count=4,
        ram=16,
        network_download_speed=1000,
        network_upload_speed=1000,
        operating_system="Linux",
    )

    expected_node_info = NodeInfo(
        gpu_model=request.gpu_model,
        vram=request.vram,
        cpu_model=request.cpu_model,
        cpu_count=request.cpu_count,
        ram=request.ram,
        network_download_speed=request.network_download_speed,
        network_upload_speed=request.network_upload_speed,
        operating_system=request.operating_system,
    )

    mock_repository = AsyncMock(spec=NodeRepository)
    response = await service.execute(request, node_id, mock_repository)
    mock_repository.save_node_info.assert_called_once_with(node_id, expected_node_info)

    assert response == PostNodeInfoResponse(response="OK")
