from distributedinference.analytics.analytics import (
    AnalyticsEvent,
    EventName,
    Analytics,
)
from distributedinference.repository.user_repository import UserRepository
from distributedinference.service import error_responses
from distributedinference.domain.user.entities import User
from distributedinference.service.auth.entities import SetUserProfileDataRequest
from distributedinference.service.auth.entities import SetUserProfileDataResponse


async def execute(
    request: SetUserProfileDataRequest,
    user: User,
    user_repository: UserRepository,
    analytics: Analytics,
) -> SetUserProfileDataResponse:
    try:
        await user_repository.update_user_profile_data(user.uid, request.data)
        analytics.track_event(user.uid, AnalyticsEvent(EventName.SET_PROFILE_DATA, {}))
    except:
        raise error_responses.ValidationError()
    return SetUserProfileDataResponse()
