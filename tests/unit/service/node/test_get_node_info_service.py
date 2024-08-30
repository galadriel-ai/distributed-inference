from unittest.mock import AsyncMock

import pytest
from uuid_extensions import uuid7

from distributedinference.domain.node.entities import NodeInfo
from distributedinference.domain.user.entities import User
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service import error_responses
from distributedinference.service.node import get_node_info_service as service
from distributedinference.service.node.entities import GetNodeInfoResponse


async def test_execute_success():
    node_info = NodeInfo(
        gpu_model="NVIDIA GTX 1080",
        vram=8,
        cpu_model="Intel i7",
        cpu_count=4,
        ram=16,
        network_download_speed=1000,
        network_upload_speed=1000,
        operating_system="Linux",
    )
    expected_response = GetNodeInfoResponse(
        gpu_model=node_info.gpu_model,
        vram=node_info.vram,
        cpu_model=node_info.cpu_model,
        cpu_count=node_info.cpu_count,
        ram=node_info.ram,
        network_download_speed=node_info.network_download_speed,
        network_upload_speed=node_info.network_upload_speed,
        operating_system=node_info.operating_system,
    )
    user = User(uid=uuid7(), name="John Doe", email="johndoe@mail.com")

    mock_repository = AsyncMock(spec=NodeRepository)
    mock_repository.get_node_info.return_value = node_info
    response = await service.execute(user, mock_repository)
    mock_repository.get_node_info.assert_called_once_with(user.uid)

    assert response == expected_response


async def test_execute_not_found():
    user = User(uid=uuid7(), name="John Doe", email="johndoe@mail.com")

    mock_repository = AsyncMock(spec=NodeRepository)
    mock_repository.get_node_info.return_value = None

    with pytest.raises(error_responses.NotFoundAPIError) as e:
        await service.execute(user, mock_repository)
        assert e is not None
