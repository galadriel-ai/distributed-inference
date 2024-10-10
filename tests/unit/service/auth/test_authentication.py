from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from uuid_extensions import uuid7

from distributedinference.domain.node.entities import NodeInfo
from distributedinference.domain.user.entities import User
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service import error_responses
from distributedinference.service.auth import authentication


async def test_api_key_missing():
    with pytest.raises(error_responses.AuthorizationMissingAPIError) as e:
        await authentication.validate_api_key("", AsyncMock())
        assert e is not None


async def test_api_key_invalid_format():
    with pytest.raises(error_responses.InvalidCredentialsAPIError) as e:
        await authentication.validate_api_key("asdasd", AsyncMock())
        assert e is not None


async def test_api_key_not_found():
    repo = AsyncMock()
    repo.get_user_by_api_key.return_value = None
    with pytest.raises(error_responses.InvalidCredentialsAPIError) as e:
        await authentication.validate_api_key("Bearer 123123", repo)
        assert e is not None


async def test_api_key_success():
    repo = AsyncMock()
    repo.get_user_by_api_key.return_value = User(
        uid=uuid7(),
        name="mock_name",
        email="mock_email",
        usage_tier_id=UUID("06706644-2409-7efd-8000-3371c5d632d3"),
    )
    user = await authentication.validate_api_key("Bearer 123123", repo)
    assert "mock_name" == user.name
    assert "mock_email" == user.email


async def test_node_name_missing():
    with pytest.raises(error_responses.NotFoundAPIError) as e:
        await authentication.validate_node_name(MagicMock(), None, AsyncMock())
        assert e is not None


async def test_node_not_found():
    mock_repository = AsyncMock(spec=NodeRepository)
    mock_repository.get_node_info_by_name.return_value = None

    with pytest.raises(error_responses.NotFoundAPIError) as e:
        await authentication.validate_node_name(MagicMock(), None, AsyncMock())
        assert e is not None


async def test_node_success():
    mock_repository = AsyncMock(spec=NodeRepository)
    node_info = NodeInfo(
        node_id=UUID("9fe247c3-71ce-4abf-8e3f-24becfab50da"),
        name="name",
        name_alias="name_alias",
    )
    mock_repository.get_node_info_by_name.return_value = node_info

    response = await authentication.validate_node_name(
        MagicMock(), "node name", mock_repository
    )
    assert response == node_info
