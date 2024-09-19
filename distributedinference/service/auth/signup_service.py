from uuid_extensions import uuid7

from distributedinference import api_logger
from distributedinference.analytics.analytics import (
    Analytics,
    EventName,
    AnalyticsEvent,
)
from distributedinference.domain.user.entities import User
from distributedinference.repository.authentication_api_repository import (
    AuthenticationApiRepository,
)
from distributedinference.repository.user_repository import UserRepository
from distributedinference.service import error_responses
from distributedinference.service.auth.entities import SignupRequest
from distributedinference.service.auth.entities import SignupResponse

logger = api_logger.get()


async def execute(
    signup_request: SignupRequest,
    auth_repo: AuthenticationApiRepository,
    user_repository: UserRepository,
    analytics: Analytics,
) -> SignupResponse:
    try:
        authentication_user_id = await auth_repo.signup_user(signup_request.email)
    except:
        logger.error("Error signing up", exc_info=True)
        raise error_responses.InvalidCredentialsAPIError()
    existing_user = await user_repository.get_user_by_authentication_id(
        authentication_user_id
    )
    if not existing_user:
        user = User(
            uid=uuid7(),
            name="console signup",
            email=signup_request.email,
            authentication_id=authentication_user_id,
        )
        await user_repository.insert_user(user)
        analytics.track_event(user.uid, AnalyticsEvent(EventName.SIGNUP, {}))
    return SignupResponse()
