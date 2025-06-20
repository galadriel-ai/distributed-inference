from stytch.core.response_base import StytchError

from distributedinference.analytics.analytics import (
    AnalyticsEvent,
    EventName,
    Analytics,
)
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
    analytics: Analytics,
) -> LoginResponse:
    user = await user_repository.get_user_by_email(login_request.email)
    if not user:
        raise error_responses.InvalidCredentialsAPIError()
    try:
        authentication = await auth_repo.login(user.email, login_request.password)
        analytics.track_event(user.uid, AnalyticsEvent(EventName.LOGIN, {}))
    except StytchError as e:
        if e.details.is_client_error and e.details.status_code == 400:
            # User is expected to do something if status code is 400
            # 401 would just mean invalid credentials
            raise error_responses.AuthorizationProviderAPIError(
                e.details.error_type
                or error_responses.InternalServerAPIError().to_code(),
                e.details.error_message,
            )
        raise error_responses.InvalidCredentialsAPIError(e.details.error_message)
    except:
        raise error_responses.InvalidCredentialsAPIError()
    return LoginResponse(
        session_token=authentication.session_token,
        onboarding_completed=user.profile_data is not None,
        user_uid=str(user.uid),
        email=user.email,
    )
