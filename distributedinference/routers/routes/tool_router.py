from fastapi import APIRouter
from fastapi import Depends

from distributedinference import api_logger, dependencies
from distributedinference.analytics.analytics import (
    Analytics,
    AnalyticsEvent,
    EventName,
)
from distributedinference.domain.user.entities import User
from distributedinference.service.auth import authentication
from distributedinference.service.tool import search_service
from distributedinference.service.tool.entities import SearchRequest
from distributedinference.service.tool.entities import SearchResponse

TAG = "Tool"
router = APIRouter(prefix="/tool")
router.tags = [TAG]

logger = api_logger.get()


@router.post(
    "/search",
    summary="Use web search.",
    description="Given a search query find results from the web.",
    response_description="Returns a list of search results.",
    response_model=SearchResponse,
)
async def search(
    request: SearchRequest,
    analytics: Analytics = Depends(dependencies.get_analytics),
    user: User = Depends(authentication.validate_api_key_header),
):
    analytics.track_event(
        user.uid, AnalyticsEvent(EventName.TOOL_CALL, {"tool": "web_search"})
    )
    return await search_service.execute(request)
