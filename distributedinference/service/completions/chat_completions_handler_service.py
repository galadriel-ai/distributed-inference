from typing import Dict
from typing import Union

from fastapi import Response
from starlette.responses import StreamingResponse

import settings
from distributedinference.analytics.analytics import Analytics
from distributedinference.domain.user.entities import User
from distributedinference.repository.metrics_queue_repository import (
    MetricsQueueRepository,
)
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.repository.rate_limit_repository import RateLimitRepository
from distributedinference.service.error_responses import RateLimitError
from distributedinference.service.completions import chat_completions_service
from distributedinference.service.completions import chat_completions_stream_service
from distributedinference.service.completions.rate_limit import check_rate_limit
from distributedinference.service.completions.entities import RateLimit
from distributedinference.service.completions.entities import ChatCompletion
from distributedinference.service.completions.entities import ChatCompletionRequest
from distributedinference.service.completions.streaming_response import (
    StreamingResponseWithStatusCode,
)


# pylint: disable=R0913
async def execute(
    request: ChatCompletionRequest,
    response: Response,
    user: User,
    node_repository: NodeRepository,
    tokens_repository: TokensRepository,
    rate_limit_repository: RateLimitRepository,
    metrics_queue_repository: MetricsQueueRepository,
    analytics: Analytics,
) -> Union[StreamingResponse, ChatCompletion]:
    rate_limit_info = await check_rate_limit(
        user, tokens_repository, rate_limit_repository
    )
    rate_limit_headers = rate_limit_to_headers(rate_limit_info)
    if rate_limit_info.rate_limited:
        raise RateLimitError(rate_limit_headers)
    request.model = _match_model_name(request.model)
    if request.stream:
        headers = {
            "X-Content-Type-Options": "nosniff",
            "Connection": "keep-alive",
            **rate_limit_headers,
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
    response.headers.update(rate_limit_headers)
    return await chat_completions_service.execute(
        user,
        request,
        node_repository=node_repository,
        tokens_repository=tokens_repository,
        metrics_queue_repository=metrics_queue_repository,
        analytics=analytics,
    )


def rate_limit_to_headers(rate_limit: RateLimit) -> Dict[str, str]:
    headers = {
        "x-ratelimit-limit-requests": str(rate_limit.rate_limit_requests),
        "x-ratelimit-limit-tokens": str(rate_limit.rate_limit_tokens or 0),
        "x-ratelimit-remaining-requests": str(
            rate_limit.rate_limit_remaining_requests or 0
        ),
        "x-ratelimit-remaining-tokens": str(
            rate_limit.rate_limit_remaining_tokens or 0
        ),
        "x-ratelimit-reset-requests": (
            f"{rate_limit.rate_limit_reset_requests}s"
            if rate_limit.rate_limit_reset_requests is not None
            else "0s"
        ),
        "x-ratelimit-reset-tokens": (
            f"{rate_limit.rate_limit_reset_tokens}s"
            if rate_limit.rate_limit_reset_tokens is not None
            else "0s"
        ),
    }
    if rate_limit.retry_after:
        headers["retry-after"] = str(rate_limit.retry_after)
    return headers


def _match_model_name(user_input: str) -> str:
    model_name = settings.MODEL_NAME_MAPPING.get(user_input.lower())

    if model_name:
        return model_name

    # forward user_input as user may provide the full model name
    return user_input
