from distributedinference.repository.authentication_api_repository import (
    AuthenticationApiRepository,
)
from distributedinference.repository.user_repository import UserRepository
from distributedinference.service import error_responses
from distributedinference.service.auth.entities import LoginRequest
from distributedinference.service.auth.entities import LoginResponse


async def execute(
    login_request: LoginRequest,
    auth_repo: AuthenticationApiRepository,
    user_repository: UserRepository,
) -> LoginResponse:
    try:
        user = await user_repository.get_user_by_username(login_request.username)
        authentication = await auth_repo.login(user.email, login_request.password)
    except:
        raise error_responses.InvalidCredentialsAPIError()
    return LoginResponse(session_token=authentication.session_token)
