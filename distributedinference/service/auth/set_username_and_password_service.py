from distributedinference.analytics.analytics import (
    Analytics,
    AnalyticsEvent,
    EventName,
)
from distributedinference.domain.auth import set_auth_provider_user_password_use_case
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
    analytics: Analytics,
) -> SetUserPasswordResponse:
    if await user_repository.get_user_by_username(link_request.username):
        raise error_responses.UsernameAlreadyExistsAPIError()
    authentication = await set_auth_provider_user_password_use_case.execute(
        link_request.token,
        link_request.password,
        auth_repo,
    )
    await user_repository.update_user_username_and_password_by_authentication_id(
        authentication.provider_user_id,
        username=link_request.username,
        is_password_set=True,
    )
    user = await user_repository.get_user_by_authentication_id(
        authentication.provider_user_id
    )
    analytics.track_event(user.uid, AnalyticsEvent(EventName.SET_USER_PASSWORD, {}))
    return SetUserPasswordResponse(session_token=authentication.session_token)
