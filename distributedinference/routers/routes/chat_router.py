from fastapi import APIRouter
from fastapi import Depends

from distributedinference import api_logger
from distributedinference import dependencies
from distributedinference.analytics.analytics import Analytics
from distributedinference.analytics.analytics import AnalyticsEvent
from distributedinference.analytics.analytics import EventName
from distributedinference.domain.user.entities import User
from distributedinference.repository.metrics_queue_repository import (
    MetricsQueueRepository,
)
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.service.auth import authentication
from distributedinference.service.completions import chat_completions_handler_service
from distributedinference.service.completions.entities import ChatCompletion
from distributedinference.service.completions.entities import ChatCompletionRequest

TAG = "Chat"
router = APIRouter(prefix="/chat")
router.tags = [TAG]

logger = api_logger.get()


@router.post(
    "/completions",
    summary="Creates a model response for the given chat conversation.",
    description="Given a list of messages comprising a conversation, the model will return a response.",
    response_description="Returns a chat completion object, or a streamed sequence of chat completion chunk objects if the request is streamed.",
    response_model=ChatCompletion,
)
# pylint: disable=too-many-arguments, R0801
async def completions(
    request: ChatCompletionRequest,
    user: User = Depends(authentication.validate_api_key_header),
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    tokens_repository: TokensRepository = Depends(dependencies.get_tokens_repository),
    metrics_queue_repository: MetricsQueueRepository = Depends(
        dependencies.get_metrics_queue_repository
    ),
    analytics: Analytics = Depends(dependencies.get_analytics),
):
    analytics.track_event(user.uid, AnalyticsEvent(EventName.CHAT_COMPLETIONS, {}))
    return await chat_completions_handler_service.execute(
        request,
        user,
        node_repository,
        tokens_repository,
        metrics_queue_repository,
        analytics,
    )
