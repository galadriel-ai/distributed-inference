from typing import Dict, Optional
from typing import Union

from fastapi import Response
from starlette.responses import StreamingResponse

import settings
from distributedinference import api_logger
from distributedinference.analytics.analytics import EventName
from distributedinference.analytics.analytics import Analytics
from distributedinference.analytics.analytics import AnalyticsEvent
from distributedinference.domain.rate_limit import rate_limit_use_case
from distributedinference.domain.rate_limit.entities import UserRateLimitResponse
from distributedinference.domain.user.entities import User
from distributedinference.repository.metrics_queue_repository import (
    MetricsQueueRepository,
)
from distributedinference.repository.tokens_queue_repository import (
    TokensQueueRepository,
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


# pylint: disable=R0913, R0801
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
    tokens_queue_repository: TokensQueueRepository,
    analytics: Analytics,
) -> Union[StreamingResponse, ChatCompletion]:

    _request_checks(request)

    rate_limit_info = await rate_limit_use_case.execute(
        request.model, user, tokens_repository, rate_limit_repository
    )
    rate_limit_headers = rate_limit_to_headers(rate_limit_info)
    if rate_limit_info.rate_limit_reason:
        analytics.track_event(
            user.uid,
            AnalyticsEvent(
                EventName.USER_RATE_LIMITED,
                {
                    "model": request.model,
                    "reason": rate_limit_info.rate_limit_reason.value,
                },
            ),
        )
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
                tokens_queue_repository=tokens_queue_repository,
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
        tokens_queue_repository=tokens_queue_repository,
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


def _check_max_tokens(request: ChatCompletionRequest) -> None:
    if not request.max_tokens:
        return None
    max_supported_tokens = settings.MODEL_MAX_TOKENS_MAPPING.get(request.model)
    if max_supported_tokens and request.max_tokens > max_supported_tokens:
        raise error_responses.ValidationTypeError(
            f"The given max_tokens exceeds the maximum the model supports: {max_supported_tokens}"
        )
    return None


# Reject the request if the response_format.type is json_object
# Reason: existing bug of vllm https://github.com/vllm-project/vllm/issues/4070
def _check_response_format(request: ChatCompletionRequest) -> None:
    if request.response_format and request.response_format.type == "json_object":
        raise error_responses.UnsupportedRequestParameterError(
            "The given response_format is not supported. Please use 'json_schema' instead"
        )


def _request_checks(request: ChatCompletionRequest) -> None:
    request.model = _match_model_name(request.model)
    if request.model not in settings.SUPPORTED_MODELS:
        raise error_responses.UnsupportedModelError(model_name=request.model)
    _check_max_tokens(request)

    if request.model not in settings.MODELS_SUPPORTING_TOOLS:
        # Required to ensure the dict value does not get set at all
        # in request.to_openai_chat_completion()
        request.tool_choice = None
        if request.tools:
            raise error_responses.ValidationTypeError(
                "The given model does not support tools"
            )

    _check_response_format(request)
