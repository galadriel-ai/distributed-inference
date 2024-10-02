from distributedinference.domain.user.entities import UserAuthenticationResponse
from distributedinference.repository.authentication_api_repository import (
    AuthenticationApiRepository,
)
from distributedinference.service import error_responses


async def execute(
    token: str,
    password: str,
    auth_repo: AuthenticationApiRepository,
) -> UserAuthenticationResponse:
    try:
        authentication = await auth_repo.authenticate_magic_link(token)
        updated_authentication = await auth_repo.set_user_password(
            password, authentication.session_token
        )
    except:
        raise error_responses.InvalidCredentialsAPIError()
    return updated_authentication
