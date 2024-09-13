from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from uuid import UUID

from distributedinference.domain.user.entities import User
from distributedinference.repository.user_repository import UserRepository
from distributedinference.service.api_key import create_api_key_service as service
from distributedinference.service.network.entities import CreateApiKeyResponse


async def test_success():
    service.utils = MagicMock()
    service.utils.to_response_date_format.return_value = "mock_datetime"
    service.secrets = MagicMock()
    api_key = "a1234567890abcd"
    service.secrets.token_urlsafe.return_value = api_key

    repository = AsyncMock(spec=UserRepository)

    response = await service.execute(
        User(
            uid=UUID("9193cd2b-f437-457e-a1f8-0df111be2ec5"),
            name="mock_name",
            email="e@e.e",
            authentication_id="mock_auth",
        ),
        repository,
    )

    assert response == CreateApiKeyResponse(
        api_key=f"gal-{api_key}", created_at="mock_datetime"
    )
