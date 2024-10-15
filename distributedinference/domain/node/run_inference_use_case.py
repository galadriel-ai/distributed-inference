import time
from typing import AsyncGenerator
from typing import Optional
from uuid import UUID

from prometheus_client import Histogram

from openai.types import CompletionUsage

from distributedinference.analytics.analytics import (
    Analytics,
    AnalyticsEvent,
    EventName,
)
from distributedinference.domain.node.entities import InferenceRequest
from distributedinference.domain.node.entities import InferenceResponse
from distributedinference.domain.node.entities import NodeMetricsIncrement
from distributedinference.domain.node.exceptions import NoAvailableNodesError
from distributedinference.repository.metrics_queue_repository import (
    MetricsQueueRepository,
)
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.repository.tokens_repository import UsageTokens

node_time_to_first_token_histogram = Histogram(
    "node_time_to_first_token_histogram",
    "Time to first token histogram in seconds by model and node uid",
    ["model_name", "node_uid"],
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10],
)


# pylint: disable=R0912, R0913, R0914
async def execute(
    user_uid: UUID,
    request: InferenceRequest,
    node_repository: NodeRepository,
    tokens_repository: TokensRepository,
    metrics_queue_repository: MetricsQueueRepository,
    analytics: Analytics,
) -> AsyncGenerator[InferenceResponse, None]:
    node = node_repository.select_node(request.model)
    if not node:
        raise NoAvailableNodesError()

    analytics.track_event(
        user_uid,
        AnalyticsEvent(
            EventName.USER_EXECUTED_INFERENCE_REQUEST, {"node_id": node.uid}
        ),
    )

    analytics.track_event(
        node.user_id,
        AnalyticsEvent(
            EventName.USER_NODE_SELECTED_FOR_INFERENCE, {"node_id": node.uid}
        ),
    )

    await node_repository.send_inference_request(node.uid, request)

    metrics_increment = NodeMetricsIncrement(node_id=node.uid)

    metrics_increment.requests_served_incerement += 1
    is_stream = bool(request.chat_request.get("stream"))
    is_include_usage: bool = (
        bool((request.chat_request.get("stream_options") or {}).get("include_usage"))
        or not is_stream
    )
    usage: Optional[CompletionUsage] = None
    request_start_time = time.time()
    first_token_time = None
    time_elapsed_after_first_token = None
    request_successful = False

    try:
        while True:
            response = await node_repository.receive_for_request(node.uid, request.id)
            if not response:
                # Nothing to check, we can break
                break
            if not first_token_time:
                first_token_time = time.time() - request_start_time
            if response.chunk:
                # overwriting the usage each time
                usage = response.chunk.usage if response.chunk else None
                if usage and not response.chunk.choices:
                    # last chunk only has usage, no choices - request is finished
                    request_successful = True
                    if is_include_usage:
                        yield response
                    # calculate the inference time starting from the first token arrival
                    if first_token_time:
                        time_elapsed_after_first_token = (
                            time.time() - request_start_time - first_token_time
                        )
                    break
                # if users doesn't need usage, we can remove it from the response
                if not is_include_usage:
                    response.chunk.usage = None
                yield response
            elif response.error:
                yield response
                break
    finally:
        await node_repository.cleanup_request(node.uid, request.id)
        if usage:
            await _save_result(
                user_uid, node.uid, request.model, usage, tokens_repository
            )
        # set only if we got at least one token
        if first_token_time is not None:
            metrics_increment.time_to_first_token = first_token_time
            # add TTFT in histogram
            node_time_to_first_token_histogram.labels(request.model, node.uid).observe(
                first_token_time
            )
        # use completion tokens / time elapsed to focus on the model generation performance
        if time_elapsed_after_first_token and usage:
            metrics_increment.inference_tokens_per_second = (
                usage.completion_tokens / time_elapsed_after_first_token
            )
        if request_successful:
            metrics_increment.requests_successful_incerement += 1
        else:
            metrics_increment.requests_failed_increment += 1
        await metrics_queue_repository.push(metrics_increment)


async def _save_result(
    user_uid: UUID,
    node_uid: UUID,
    model_name: str,
    usage: CompletionUsage,
    repository: TokensRepository,
):
    # TODO: in the background?
    await repository.insert_usage_tokens(
        UsageTokens(
            consumer_user_profile_id=user_uid,
            producer_node_info_id=node_uid,
            model_name=model_name,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
        )
    )
