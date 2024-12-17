from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from uuid_extensions import uuid7

from distributedinference.domain.node.entities import FullNodeInfo
from distributedinference.domain.node.entities import NodeSpecs
from distributedinference.repository.connection import DBConnection
from distributedinference.repository.user_node_repository import (
    SQL_UPDATE_NODE_INFO,
)
from distributedinference.repository.user_node_repository import UserNodeRepository

NODE_UUID = UUID("40c95432-8b2c-4208-bdf4-84f49ff957a3")


@pytest.fixture
def session_provider():
    mock_session_provider = MagicMock(spec=DBConnection)
    return mock_session_provider


@pytest.fixture
def user_node_repository(session_provider):
    return UserNodeRepository(
        session_provider,
        session_provider,
    )


async def test_save_node_info(user_node_repository, session_provider):
    node_id = uuid7()

    node_info = FullNodeInfo(
        name="name",
        name_alias="user alias",
        node_id=NODE_UUID,
        created_at=datetime(2020, 1, 1),
        specs=NodeSpecs(
            gpu_model="NVIDIA GTX 1080",
            vram=8,
            gpu_count=1,
            cpu_model="Intel i7",
            cpu_count=8,
            ram=16,
            power_limit=350,
            network_download_speed=1000,
            network_upload_speed=1000,
            operating_system="Linux",
            version="0.0.1",
        ),
    )

    mock_session = AsyncMock()
    session_provider.get.return_value.__aenter__.return_value = mock_session

    await user_node_repository.save_node_info(node_id, node_info)

    mock_session.execute.assert_called_once()
    args, kwargs = mock_session.execute.call_args

    assert args[0].text == SQL_UPDATE_NODE_INFO

    data = args[1]
    assert data["user_profile_id"] == node_id
    assert data["gpu_model"] == node_info.specs.gpu_model
    assert data["vram"] == node_info.specs.vram
    assert data["gpu_count"] == node_info.specs.gpu_count
    assert data["cpu_model"] == node_info.specs.cpu_model
    assert data["cpu_count"] == node_info.specs.cpu_count
    assert data["ram"] == node_info.specs.ram
    assert data["power_limit"] == node_info.specs.power_limit
    assert data["network_download_speed"] == node_info.specs.network_download_speed
    assert data["network_upload_speed"] == node_info.specs.network_upload_speed
    assert data["operating_system"] == node_info.specs.operating_system
    assert data["version"] == node_info.specs.version
    assert "created_at" in data
    assert "last_updated_at" in data

    mock_session.commit.assert_called_once()
