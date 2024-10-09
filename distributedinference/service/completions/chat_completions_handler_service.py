from typing import Union

from starlette.responses import StreamingResponse

from distributedinference.analytics.analytics import Analytics
from distributedinference.domain.user.entities import User
from distributedinference.repository.metrics_queue_repository import (
    MetricsQueueRepository,
)
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.service.completions import chat_completions_service
from distributedinference.service.completions import chat_completions_stream_service
from distributedinference.service.completions.entities import ChatCompletion
from distributedinference.service.completions.entities import ChatCompletionRequest
from distributedinference.service.completions.streaming_response import (
    StreamingResponseWithStatusCode,
)


# pylint: disable=R0913
async def execute(
    request: ChatCompletionRequest,
    user: User,
    node_repository: NodeRepository,
    tokens_repository: TokensRepository,
    metrics_queue_repository: MetricsQueueRepository,
    analytics: Analytics,
) -> Union[StreamingResponse, ChatCompletion]:
    if request.stream:
        headers = {
            "X-Content-Type-Options": "nosniff",
            "Connection": "keep-alive",
        }
        return StreamingResponseWithStatusCode(
            chat_completions_stream_service.execute(
                user,
                request,
                node_repository=node_repository,
                tokens_repository=tokens_repository,
                metrics_queue_repository=metrics_queue_repository,
                analytics=analytics,
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
        analytics=analytics,
    )
