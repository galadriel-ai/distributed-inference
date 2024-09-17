from distributedinference.repository.authentication_api_repository import (
    AuthenticationApiRepository,
)
from distributedinference.repository.user_repository import UserRepository
from distributedinference.service import error_responses
from distributedinference.service.auth.entities import SetUserPasswordRequest
from distributedinference.service.auth.entities import SetUserPasswordResponse


async def execute(
    link_request: SetUserPasswordRequest,
    auth_repo: AuthenticationApiRepository,
    user_repository: UserRepository,
) -> SetUserPasswordResponse:
    if await user_repository.get_user_by_username(link_request.username):
        raise error_responses.UsernameAlreadyExistsAPIError()
    try:
        authentication = await auth_repo.authenticate_magic_link(link_request.token)
        updated_authentication = await auth_repo.set_user_password(
            link_request.password, authentication.session_token
        )
    except:
        raise error_responses.InvalidCredentialsAPIError()
    await user_repository.update_user_username_and_password_by_authentication_id(
        authentication.provider_user_id,
        username=link_request.username,
        is_password_set=True,
    )
    # TODO: decide if user should be logged in here or log in with password, product question
    return SetUserPasswordResponse(session_token=updated_authentication.session_token)
