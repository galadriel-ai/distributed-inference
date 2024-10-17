from distributedinference.analytics.analytics import Analytics
from distributedinference.analytics.analytics import AnalyticsEvent
from distributedinference.analytics.analytics import EventName
from distributedinference.repository.authentication_api_repository import (
    AuthenticationApiRepository,
)
from distributedinference.repository.user_repository import UserRepository
from distributedinference.service import error_responses
from distributedinference.service.auth.entities import ResetUserPasswordRequest
from distributedinference.service.auth.entities import ResetUserPasswordResponse


async def execute(
    link_request: ResetUserPasswordRequest,
    auth_repo: AuthenticationApiRepository,
    user_repository: UserRepository,
    analytics: Analytics,
) -> ResetUserPasswordResponse:
    try:
        authentication = await auth_repo.set_user_password(
            link_request.password,
            link_request.token,
        )
    except Exception:
        raise error_responses.InvalidCredentialsAPIError()
    user = await user_repository.get_user_by_authentication_id(
        authentication.provider_user_id
    )
    analytics.track_event(user.uid, AnalyticsEvent(EventName.RESET_USER_PASSWORD, {}))
    return ResetUserPasswordResponse(
        email=user.email,
        user_uid=str(user.uid),
        session_token=authentication.session_token,
    )
