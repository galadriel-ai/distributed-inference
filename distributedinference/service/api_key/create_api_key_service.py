from distributedinference.domain.api_key import create_api_key_use_case
from distributedinference.domain.user.entities import User
from distributedinference.repository.user_repository import UserRepository
from distributedinference.service.network.entities import CreateApiKeyResponse


async def execute(user: User, repo: UserRepository) -> CreateApiKeyResponse:
    created_api_key = await create_api_key_use_case.execute(user, repo)
    return CreateApiKeyResponse(
        api_key_id=str(created_api_key.api_key_id),
        api_key=created_api_key.api_key,
        created_at=created_api_key.created_at,
    )
