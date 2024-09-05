import time
from typing import AsyncGenerator
from typing import Optional
from uuid import UUID

from openai.types import CompletionUsage

from distributedinference.domain.node.exceptions import NoAvailableNodesError
from distributedinference.domain.node.entities import InferenceRequest
from distributedinference.domain.node.entities import InferenceResponse
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.repository.tokens_repository import UsageTokens


async def execute(
    user_uid: UUID,
    request: InferenceRequest,
    node_repository: NodeRepository,
    tokens_repository: TokensRepository,
) -> AsyncGenerator[InferenceResponse, None]:
    node = node_repository.select_node(request.model)
    if not node:
        raise NoAvailableNodesError()
    await node_repository.send_inference_request(node.uid, request)
    async with node.metrics.lock:
        node.metrics.requests_served += 1
    is_stream = bool(request.chat_request.get("stream"))
    is_include_usage: bool = bool(
        (request.chat_request.get("stream_options") or {}).get("include_usage")
    )
    usage: Optional[CompletionUsage] = None
    request_start_time = time.time()
    first_token_time = None
    request_successful = False
    try:
        while True:
            response = await node_repository.receive_for_request(node.uid, request.id)
            if response.error:
                yield response
                break
            if not first_token_time:
                first_token_time = time.time() - request_start_time

            # overwriting the usage each time
            usage = response.chunk.usage
            yield response
            if is_stream and is_include_usage:
                # If is_stream and is_include_usage last chunk has no choices, only usage info
                if not len(response.chunk.choices):
                    break
            else:
                if response.chunk.choices[0].finish_reason == "stop":
                    request_successful = True
                    break
    finally:
        await node_repository.cleanup_request(node.uid, request.id)
        if usage:
            await _save_result(
                user_uid, node.uid, request.model, usage, tokens_repository
            )
        async with node.metrics.lock:
            # set only if we got at least one token
            if first_token_time is not None:
                node.metrics.time_to_first_token = first_token_time
            if request_successful:
                node.metrics.requests_successful += 1
            else:
                node.metrics.requests_failed += 1
        await node_repository.save_node_metrics(node.uid, node.metrics)


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
            producer_user_profile_id=node_uid,
            model_name=model_name,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
        )
    )
