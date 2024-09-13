from typing import List

from distributedinference.domain.user.entities import ApiKey
from distributedinference.domain.user.entities import User
from distributedinference.repository.user_repository import UserRepository
from distributedinference.service import utils
from distributedinference.service.network.entities import GetApiKeysResponse
from distributedinference.service.network.entities import UserApiKey

API_KEY_PREFIX_LENGTH: int = 10


async def execute(user: User, repo: UserRepository) -> GetApiKeysResponse:
    api_keys = await repo.get_user_api_keys(user.uid)
    return GetApiKeysResponse(api_keys=_get_formatted_api_keys(api_keys))


def _get_formatted_api_keys(api_keys: List[ApiKey]) -> List[UserApiKey]:
    return [
        UserApiKey(
            api_key_prefix=key.api_key[:API_KEY_PREFIX_LENGTH],
            created_at=utils.to_response_date_format(key.created_at),
        )
        for key in api_keys
    ]
