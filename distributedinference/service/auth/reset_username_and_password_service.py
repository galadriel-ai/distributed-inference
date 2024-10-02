from distributedinference.analytics.analytics import Analytics
from distributedinference.analytics.analytics import AnalyticsEvent
from distributedinference.analytics.analytics import EventName
from distributedinference.domain.auth import set_auth_provider_user_password_use_case
from distributedinference.repository.authentication_api_repository import (
    AuthenticationApiRepository,
)
from distributedinference.repository.user_repository import UserRepository
from distributedinference.service.auth.entities import ResetUserPasswordRequest
from distributedinference.service.auth.entities import ResetUserPasswordResponse


async def execute(
    link_request: ResetUserPasswordRequest,
    auth_repo: AuthenticationApiRepository,
    user_repository: UserRepository,
    analytics: Analytics,
) -> ResetUserPasswordResponse:
    authentication = await set_auth_provider_user_password_use_case.execute(
        link_request.token,
        link_request.password,
        auth_repo,
    )
    user = await user_repository.get_user_by_authentication_id(
        authentication.provider_user_id
    )
    analytics.track_event(user.uid, AnalyticsEvent(EventName.RESET_USER_PASSWORD, {}))
    return ResetUserPasswordResponse(session_token=authentication.session_token)
