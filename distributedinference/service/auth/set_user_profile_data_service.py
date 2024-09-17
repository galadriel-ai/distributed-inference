from distributedinference.repository.authentication_api_repository import (
    AuthenticationApiRepository,
)
from distributedinference.repository.user_repository import UserRepository
from distributedinference.service import error_responses
from distributedinference.domain.user.entities import User
from distributedinference.service.auth.entities import SetUserProfileDataRequest
from distributedinference.service.auth.entities import SetUserProfileDataResponse


async def execute(
    request: SetUserProfileDataRequest,
    user: User,
    user_repository: UserRepository,
) -> SetUserProfileDataResponse:
    try:
        await user_repository.update_user_profile_data(user.uid, request.data)
    except:
        raise error_responses.ValidationError()
    return SetUserProfileDataResponse()
