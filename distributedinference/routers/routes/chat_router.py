from fastapi import APIRouter
from fastapi import Depends
from starlette.responses import StreamingResponse

from distributedinference import api_logger
from distributedinference import dependencies
from distributedinference.analytics.analytics import (
    Analytics,
    EventName,
    AnalyticsEvent,
)
from distributedinference.domain.user.entities import User
from distributedinference.repository.metrics_queue_repository import (
    MetricsQueueRepository,
)
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.service.auth import authentication
from distributedinference.service.completions import chat_completions_service
from distributedinference.service.completions import chat_completions_stream_service
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
    if request.stream:
        headers = {
            "X-Content-Type-Options": "nosniff",
            "Connection": "keep-alive",
        }
        return StreamingResponse(
            chat_completions_stream_service.execute(
                user,
                request,
                node_repository=node_repository,
                tokens_repository=tokens_repository,
                metrics_queue_repository=metrics_queue_repository,
            ),
            headers=headers,
            media_type="text/event-stream",
        )
    return await chat_completions_service.execute(
        user,
        request,
        node_repository=node_repository,
        tokens_repository=tokens_repository,
        metrics_queue_repository=metrics_queue_repository,
    )
