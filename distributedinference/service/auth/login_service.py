from distributedinference.repository.authentication_api_repository import AuthenticationApiRepository
from distributedinference.service.auth.entities import LoginRequest
from distributedinference.service.auth.entities import LoginResponse


async def execute(
    login_request: LoginRequest,
    auth_repo: AuthenticationApiRepository,
) -> LoginResponse:
    # TODO: handle errors, wrong password etc
    authentication = await auth_repo.login(login_request.email, login_request.password)
    return LoginResponse(
        session_token=authentication.session_token
    )
