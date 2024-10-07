from distributedinference import api_logger
from distributedinference.analytics.analytics import Analytics
from distributedinference.analytics.analytics import AnalyticsEvent
from distributedinference.analytics.analytics import EventName
from distributedinference.domain.user.entities import User
from distributedinference.repository.user_repository import UserRepository
from distributedinference.service import error_responses
from distributedinference.service.auth.entities import SetUserProfileDataRequest
from distributedinference.service.auth.entities import SetUserProfileDataResponse

logger = api_logger.get()


async def execute(
    request: SetUserProfileDataRequest,
    user: User,
    user_repository: UserRepository,
    analytics: Analytics,
) -> SetUserProfileDataResponse:
    try:
        await user_repository.update_user_profile_data(user.uid, request.data)
        analytics.track_event(user.uid, AnalyticsEvent(EventName.SET_PROFILE_DATA, {}))
        analytics.identify_user(user, request.data)
    except:
        logger.error(f"Error inserting user {user.uid} profile data", exc_info=True)
        raise error_responses.ValidationError()
    return SetUserProfileDataResponse()
