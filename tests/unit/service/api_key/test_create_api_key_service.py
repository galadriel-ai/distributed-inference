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
    api_key_id = UUID("a29d1a91-3268-4c3c-9b2d-1f5841702192")
    repository.insert_api_key.return_value = api_key_id

    response = await service.execute(
        User(
            uid=UUID("9193cd2b-f437-457e-a1f8-0df111be2ec5"),
            name="mock_name",
            email="e@e.e",
            authentication_id="mock_auth",
            usage_tier_id=UUID("06706644-2409-7efd-8000-3371c5d632d3"),
        ),
        repository,
    )

    assert response == CreateApiKeyResponse(
        api_key_id=str(api_key_id), api_key=f"gal-{api_key}", created_at="mock_datetime"
    )
