from uuid import UUID

from uuid_extensions import uuid7

import settings
from distributedinference.analytics.analytics import Analytics
from distributedinference.analytics.analytics import AnalyticsEvent
from distributedinference.analytics.analytics import EventName
from distributedinference.domain.auth import signup_user_use_case
from distributedinference.domain.auth.entities import UserSignup
from distributedinference.domain.user.entities import User
from distributedinference.repository.authentication_api_repository import (
    AuthenticationApiRepository,
)
from distributedinference.repository.user_repository import UserRepository
from distributedinference.service import error_responses
from distributedinference.service.auth.entities import SignupRequest
from distributedinference.service.auth.entities import SignupResponse


async def execute(
    signup_request: SignupRequest,
    auth_repo: AuthenticationApiRepository,
    user_repository: UserRepository,
    analytics: Analytics,
) -> SignupResponse:
    if await user_repository.get_user_by_email(signup_request.email):
        raise error_responses.UsernameAlreadyExistsAPIError()
    authentication = await signup_user_use_case.execute(
        UserSignup(
            password=signup_request.password,
            email=signup_request.email,
        ),
        auth_repo,
    )

    user = User(
        uid=uuid7(),
        name="console signup",
        email=signup_request.email,
        authentication_id=authentication.provider_user_id,
        usage_tier_id=UUID(settings.DEFAULT_USAGE_TIER_UUID),
    )
    await user_repository.insert_user(user, is_password_set=True)
    analytics.track_event(user.uid, AnalyticsEvent(EventName.SIGNUP, {}))
    analytics.identify_user(user)

    return SignupResponse(
        email=signup_request.email,
        user_uid=str(user.uid),
        session_token=authentication.session_token,
    )
