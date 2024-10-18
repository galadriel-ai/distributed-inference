from datetime import datetime
from unittest.mock import AsyncMock

from uuid_extensions import uuid7

import settings
from distributedinference.domain.api_key.entities import CreatedApiKey
from distributedinference.domain.user.entities import ApiKey
from distributedinference.domain.user.entities import User
from distributedinference.repository.user_repository import UserRepository
from distributedinference.service.api_key import get_example_api_key_service as service
from distributedinference.service.network.entities import GetUserApiKeyExampleResponse


async def test_success_key_exists():
    service.create_api_key_use_case = AsyncMock()
    user = User(
        uid=uuid7(),
        name="name",
        email="email",
        usage_tier_id=settings.DEFAULT_USAGE_TIER_UUID,
    )
    repo = AsyncMock(spec=UserRepository)
    repo.get_user_api_keys.return_value = [
        ApiKey(uid=uuid7(), api_key="api-key-0", created_at=datetime.now()),
        ApiKey(uid=uuid7(), api_key="api-key-1", created_at=datetime.now()),
    ]
    response = await service.execute(user, repo)
    assert response == GetUserApiKeyExampleResponse(api_key="api-key-0")


async def test_success_creates_key():
    service.create_api_key_use_case = AsyncMock()
    service.create_api_key_use_case.execute.return_value = CreatedApiKey(
        api_key_id=uuid7(),
        api_key="api-key-0",
        created_at="created_at",
    )

    user = User(
        uid=uuid7(),
        name="name",
        email="email",
        usage_tier_id=settings.DEFAULT_USAGE_TIER_UUID,
    )
    repo = AsyncMock(spec=UserRepository)
    repo.get_user_api_keys.return_value = []
    response = await service.execute(user, repo)
    assert response == GetUserApiKeyExampleResponse(api_key="api-key-0")
