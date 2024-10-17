from distributedinference import api_logger
from distributedinference.repository.authentication_api_repository import (
    AuthenticationApiRepository,
)
from distributedinference.repository.user_repository import UserRepository
from distributedinference.service import error_responses
from distributedinference.service.auth.entities import ValidateEmailRequest
from distributedinference.service.auth.entities import ValidateEmailResponse

logger = api_logger.get()


async def execute(
    signup_request: ValidateEmailRequest,
    auth_repo: AuthenticationApiRepository,
    user_repository: UserRepository,
) -> ValidateEmailResponse:
    if not await user_repository.get_user_by_email(signup_request.email):
        raise error_responses.NotFoundAPIError("Email not found")
    try:
        await auth_repo.reset_user(signup_request.email)
    except:
        logger.error("Error resetting user email up", exc_info=True)
        raise error_responses.InvalidCredentialsAPIError()
    return ValidateEmailResponse()
