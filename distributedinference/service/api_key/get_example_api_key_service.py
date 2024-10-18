from distributedinference.domain.api_key import create_api_key_use_case
from distributedinference.domain.user.entities import User
from distributedinference.repository.user_repository import UserRepository
from distributedinference.service.network.entities import GetUserApiKeyExampleResponse


async def execute(user: User, repo: UserRepository) -> GetUserApiKeyExampleResponse:
    api_keys = await repo.get_user_api_keys(user.uid)
    if not len(api_keys):
        created_api_key = await create_api_key_use_case.execute(user, repo)
        api_key = created_api_key.api_key
    else:
        api_key = api_keys[0].api_key
    return GetUserApiKeyExampleResponse(api_key=api_key)
