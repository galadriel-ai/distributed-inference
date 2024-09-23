from distributedinference.domain.user.entities import User
from distributedinference.repository.user_repository import UserRepository
from distributedinference.service import utils
from distributedinference.service.network.entities import DeleteApiKeyRequest
from distributedinference.service.network.entities import DeleteApiKeyResponse


async def execute(
    request: DeleteApiKeyRequest, user: User, user_repository: UserRepository
) -> DeleteApiKeyResponse:
    api_key_uid = utils.parse_uuid(request.api_key_id)
    await user_repository.delete_api_key(user.uid, api_key_uid)
    return DeleteApiKeyResponse()
