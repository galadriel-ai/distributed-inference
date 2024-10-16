from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest
from uuid import UUID
from uuid_extensions import uuid7

from distributedinference.domain.user.entities import User
from distributedinference.domain.user.entities import UserAuthenticationResponse
from distributedinference.repository.authentication_api_repository import (
    AuthenticationApiRepository,
)
from distributedinference.repository.user_repository import UserRepository
from distributedinference.service import error_responses
from distributedinference.service.auth import (
    reset_username_and_password_service as service,
)
from distributedinference.service.auth.entities import ResetUserPasswordRequest


async def test_success():
    auth_repo = AsyncMock(spec=AuthenticationApiRepository)
    auth_repo.authenticate_magic_link.return_value = UserAuthenticationResponse(
        provider_user_id="mock_provider_user_id",
        session_token="mock_session_token",
    )
    auth_repo.set_user_password.return_value = UserAuthenticationResponse(
        provider_user_id="mock_provider_user_id",
        session_token="mock_session_token_2",
    )

    user_repo = AsyncMock(spec=UserRepository)
    user_repo.get_user_by_authentication_id.return_value = User(
        uid=uuid7(),
        name="mock_name",
        email="mock_email",
        username="mock_username",
        usage_tier_id=UUID("06706644-2409-7efd-8000-3371c5d632d3"),
    )
    analytics = MagicMock()
    response = await service.execute(
        ResetUserPasswordRequest(token="token", password="password"),
        auth_repo,
        user_repo,
        analytics,
    )
    assert response.session_token == "mock_session_token_2"
    analytics.track_event.assert_called_once()


async def test_auth_error():
    auth_repo = AsyncMock(spec=AuthenticationApiRepository)
    auth_repo.authenticate_magic_link = AsyncMock(side_effect=Exception)
    auth_repo.set_user_password.return_value = UserAuthenticationResponse(
        provider_user_id="mock_provider_user_id",
        session_token="mock_session_token_2",
    )

    analytics = MagicMock()

    with pytest.raises(error_responses.InvalidCredentialsAPIError) as e:
        await service.execute(
            ResetUserPasswordRequest(token="token", password="password"),
            auth_repo,
            AsyncMock(),
            analytics,
        )
        assert e is not None
    analytics.track_event.assert_not_called()
