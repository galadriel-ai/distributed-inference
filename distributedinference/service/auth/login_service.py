from distributedinference.repository.authentication_api_repository import (
    AuthenticationApiRepository,
)
from distributedinference.service import error_responses
from distributedinference.service.auth.entities import LoginRequest
from distributedinference.service.auth.entities import LoginResponse


async def execute(
    login_request: LoginRequest,
    auth_repo: AuthenticationApiRepository,
) -> LoginResponse:
    try:
        authentication = await auth_repo.login(
            login_request.email, login_request.password
        )
    except:
        raise error_responses.InvalidCredentialsAPIError()
    return LoginResponse(session_token=authentication.session_token)
