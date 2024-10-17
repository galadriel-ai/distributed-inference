from distributedinference.domain.auth.entities import UserSignup
from distributedinference.domain.user.entities import UserAuthenticationResponse
from distributedinference.repository.authentication_api_repository import (
    AuthenticationApiRepository,
)
from distributedinference.service import error_responses


async def execute(
    signup: UserSignup,
    auth_repo: AuthenticationApiRepository,
) -> UserAuthenticationResponse:
    try:
        updated_authentication = await auth_repo.signup_with_password(
            signup.email, signup.password
        )
    except Exception:
        raise error_responses.InvalidCredentialsAPIError()
    return updated_authentication
