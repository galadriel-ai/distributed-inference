from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from uuid_extensions import uuid7

from distributedinference.domain.user.entities import User
from distributedinference.service import error_responses
from distributedinference.service.auth import authentication


async def test_api_key_missing():
    with pytest.raises(error_responses.AuthorizationMissingAPIError) as e:
        await authentication._validate_api_key("", AsyncMock())
        assert e is not None


async def test_api_key_invalid_format():
    with pytest.raises(error_responses.InvalidCredentialsAPIError) as e:
        await authentication._validate_api_key("asdasd", AsyncMock())
        assert e is not None


async def test_api_key_not_found():
    repo = AsyncMock()
    repo.get_user_by_api_key.return_value = None
    with pytest.raises(error_responses.InvalidCredentialsAPIError) as e:
        await authentication._validate_api_key("Bearer 123123", repo)
        assert e is not None


async def test_api_key_success():
    repo = AsyncMock()
    repo.get_user_by_api_key.return_value = User(
        uid=uuid7(),
        name="mock_name",
        email="mock_email",
    )
    user = await authentication._validate_api_key("Bearer 123123", repo)
    assert "mock_name" == user.name
    assert "mock_email" == user.email
