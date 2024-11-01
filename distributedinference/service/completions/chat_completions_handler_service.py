from typing import Dict, Optional
from typing import Union

from fastapi import Response
from starlette.responses import StreamingResponse

import settings
from distributedinference import api_logger
from distributedinference.analytics.analytics import Analytics
from distributedinference.domain.rate_limit import rate_limit_use_case
from distributedinference.domain.rate_limit.entities import UserRateLimitResponse
from distributedinference.domain.user.entities import User
from distributedinference.repository.metrics_queue_repository import (
    MetricsQueueRepository,
)
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.rate_limit_repository import RateLimitRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.service import error_responses
from distributedinference.service.completions import chat_completions_service
from distributedinference.service.completions import chat_completions_stream_service
from distributedinference.service.completions.entities import ChatCompletion
from distributedinference.service.completions.entities import ChatCompletionRequest
from distributedinference.service.completions.streaming_response import (
    StreamingResponseWithStatusCode,
)
from distributedinference.service.error_responses import RateLimitError
from distributedinference.utils.timer import async_timer

logger = api_logger.get()


# pylint: disable=R0913
@async_timer("chat_completions_handler_service.execute", logger=logger)
async def execute(
    request: ChatCompletionRequest,
    response: Response,
    user: User,
    forwarding_from: Optional[str],
    node_repository: NodeRepository,
    tokens_repository: TokensRepository,
    rate_limit_repository: RateLimitRepository,
    metrics_queue_repository: MetricsQueueRepository,
    analytics: Analytics,
) -> Union[StreamingResponse, ChatCompletion]:
    request.model = _match_model_name(request.model)

    if request.tools and request.model not in settings.MODELS_SUPPORTING_TOOLS:
        raise error_responses.ValidationTypeError(
            "The given model does not support tools"
        )

    rate_limit_info = await rate_limit_use_case.execute(
        request.model, user, tokens_repository, rate_limit_repository
    )
    rate_limit_headers = rate_limit_to_headers(rate_limit_info)
    if rate_limit_info.rate_limited:
        raise RateLimitError(rate_limit_headers)
    if request.stream:
        headers = {
            "X-Content-Type-Options": "nosniff",
            "Connection": "keep-alive",
            **rate_limit_headers,
        }
        return StreamingResponseWithStatusCode(
            chat_completions_stream_service.execute(
                user,
                forwarding_from,
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
        forwarding_from,
        request,
        node_repository=node_repository,
        tokens_repository=tokens_repository,
        metrics_queue_repository=metrics_queue_repository,
        analytics=analytics,
    )


def rate_limit_to_headers(rate_limit: UserRateLimitResponse) -> Dict[str, str]:
    headers = {
        "x-ratelimit-limit-requests": str(rate_limit.rate_limit_day.max_requests),
        "x-ratelimit-limit-tokens": str(rate_limit.rate_limit_minute.max_tokens or 0),
        "x-ratelimit-remaining-requests": str(
            rate_limit.rate_limit_day.remaining_requests or 0
        ),
        "x-ratelimit-remaining-tokens": str(
            rate_limit.rate_limit_minute.remaining_tokens or 0
        ),
        "x-ratelimit-reset-requests": (
            f"{rate_limit.rate_limit_day.reset_requests}s"
            if rate_limit.rate_limit_day.reset_requests is not None
            else "0s"
        ),
        "x-ratelimit-reset-tokens": (
            f"{rate_limit.rate_limit_minute.reset_tokens}s"
            if rate_limit.rate_limit_minute.reset_tokens is not None
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
