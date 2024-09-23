from datetime import datetime
from unittest.mock import AsyncMock
from uuid import UUID

from uuid_extensions import uuid7

from distributedinference.domain.user.entities import ApiKey
from distributedinference.domain.user.entities import User
from distributedinference.repository.user_repository import UserRepository
from distributedinference.service.api_key import get_api_keys_service as service
from distributedinference.service.network.entities import GetApiKeysResponse
from distributedinference.service.network.entities import UserApiKey


async def test_success():
    repository = AsyncMock(spec=UserRepository)
    returned_api_keys = [
        ApiKey(uid=uuid7(), api_key="1234567890abc", created_at=datetime(2024, 1, 1)),
        ApiKey(uid=uuid7(), api_key="1234567890abc", created_at=datetime(2024, 1, 2)),
    ]
    repository.get_user_api_keys.return_value = returned_api_keys

    response = await service.execute(
        User(
            uid=UUID("9193cd2b-f437-457e-a1f8-0df111be2ec5"),
            name="mock_name",
            email="e@e.e",
            authentication_id="mock_auth",
        ),
        repository,
    )

    assert response == GetApiKeysResponse(
        api_keys=[
            UserApiKey(
                api_key_id=str(returned_api_keys[0].uid),
                api_key_prefix="1234567890",
                created_at="2024-01-01T00:00:00Z",
            ),
            UserApiKey(
                api_key_id=str(returned_api_keys[1].uid),
                api_key_prefix="1234567890",
                created_at="2024-01-02T00:00:00Z",
            ),
        ]
    )
