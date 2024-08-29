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
    node_id = node_repository.select_node(request.model)
    if not node_id:
        raise NoAvailableNodesError()
    await node_repository.send_inference_request(node_id, request)
    is_stream = bool(request.chat_request.get("stream"))
    is_include_usage: bool = bool(
        (request.chat_request.get("stream_options") or {}).get("include_usage")
    )
    usage: Optional[CompletionUsage] = None
    try:
        while True:
            response = await node_repository.receive_for_request(node_id, request.id)
            # overwriting the usage each time
            usage = response.chunk.usage
            yield response
            if is_stream and is_include_usage:
                # If is_stream and is_include_usage last chunk has no choices, only usage info
                if not len(response.chunk.choices):
                    break
            else:
                if response.chunk.choices[0].finish_reason == "stop":
                    break
            if response.error:
                break
    finally:
        await node_repository.cleanup_request(node_id, request.id)
        await _save_result(user_uid, node_id, request.model, usage, tokens_repository)


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
