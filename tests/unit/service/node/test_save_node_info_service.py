import pytest
from unittest.mock import AsyncMock
from uuid_extensions import uuid7
from distributedinference.domain.node.entities import NodeInfo
from distributedinference.service.node.entities import NodeInfoRequest, NodeInfoResponse
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.node import save_node_info_service as service


async def test_execute_success():
    node_id = uuid7()
    request = NodeInfoRequest(
        gpu_model="NVIDIA GTX 1080",
        vram=8,
        cpu_model="Intel i7",
        ram=16,
        network_speed=1000,
        operating_system="Linux",
    )

    expected_node_info = NodeInfo(
        gpu_model=request.gpu_model,
        vram=request.vram,
        cpu_model=request.cpu_model,
        ram=request.ram,
        network_speed=request.network_speed,
        operating_system=request.operating_system,
    )

    mock_repository = AsyncMock(spec=NodeRepository)
    response = await service.execute(request, node_id, mock_repository)
    mock_repository.save_node_info.assert_called_once_with(node_id, expected_node_info)

    assert response == NodeInfoResponse(response="OK")
