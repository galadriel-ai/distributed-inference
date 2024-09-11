from uuid_extensions import uuid7

from distributedinference.domain.user.entities import User
from distributedinference.repository.authentication_api_repository import (
    AuthenticationApiRepository,
)
from distributedinference.repository.user_repository import UserRepository
from distributedinference.service import error_responses
from distributedinference.service.auth.entities import SignupRequest
from distributedinference.service.auth.entities import SignupResponse


async def execute(
    signup_request: SignupRequest,
    auth_repo: AuthenticationApiRepository,
    user_repository: UserRepository,
) -> SignupResponse:
    try:
        authentication_user_id = await auth_repo.signup_user(signup_request.email)
    except:
        raise error_responses.InvalidCredentialsAPIError()
    existing_user = await user_repository.get_user_by_authentication_id(
        authentication_user_id
    )
    if not existing_user:
        await user_repository.insert_user(
            User(
                uid=uuid7(),
                name="console signup",
                email=signup_request.email,
                authentication_id=authentication_user_id,
            )
        )
    return SignupResponse()
