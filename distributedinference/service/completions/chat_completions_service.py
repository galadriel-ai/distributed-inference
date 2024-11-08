import time
from typing import List
from typing import Optional

from openai.types.chat import ChatCompletionMessage
from openai.types.chat import ChatCompletionMessageToolCall
from openai.types.chat import CompletionCreateParams
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_chunk import ChoiceDeltaToolCall
from uuid_extensions import uuid7

from distributedinference import api_logger
from distributedinference.analytics.analytics import Analytics
from distributedinference.domain.node.entities import InferenceRequest
from distributedinference.domain.node.exceptions import NoAvailableNodesError
from distributedinference.domain.node.run_inference_use_case import InferenceExecutor
from distributedinference.domain.user.entities import User
from distributedinference.repository.metrics_queue_repository import (
    MetricsQueueRepository,
)
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.service import error_responses
from distributedinference.service.completions import (
    convert_tool_call_chunks_to_non_streaming,
)
from distributedinference.service.completions.entities import ChatCompletion
from distributedinference.service.completions.entities import ChatCompletionRequest
from distributedinference.utils.timer import async_timer

logger = api_logger.get()


# pylint: disable=R0913
@async_timer("chat_completions_service.execute", logger=logger)
async def execute(
    user: User,
    forwarding_from: Optional[str],
    request: ChatCompletionRequest,
    node_repository: NodeRepository,
    tokens_repository: TokensRepository,
    metrics_queue_repository: MetricsQueueRepository,
    analytics: Analytics,
) -> ChatCompletion:
    try:
        chat_request: CompletionCreateParams = await request.to_openai_chat_completion()
    except:
        raise error_responses.ValidationError()

    inference_request = InferenceRequest(
        id=str(uuid7()),
        model=request.model,
        chat_request=chat_request,
    )
    try:
        response = ""
        tool_response_chunks = []
        usage = None
        executor = InferenceExecutor(
            node_repository=node_repository,
            tokens_repository=tokens_repository,
            metrics_queue_repository=metrics_queue_repository,
            analytics=analytics,
        )
        async for inference_response in executor.execute(
            user_uid=user.uid,
            api_key=user.currently_using_api_key,
            forwarding_from=forwarding_from,
            request=inference_request,
        ):
            if inference_response.error:
                raise error_responses.InferenceError(
                    node_id=inference_response.node_id,
                    status_code=inference_response.error.status_code,
                    message_extra=inference_response.error.message,
                )

            response_chunk = inference_response.chunk
            if not response_chunk:
                continue

            if choices := response_chunk.choices:
                first_choice = choices[0]
                content = first_choice.delta.content
                if content:
                    response += content

                if tool_calls := first_choice.delta.tool_calls:
                    # tool_calls is a list, need to extend!
                    tool_response_chunks.extend(tool_calls)
            if response_chunk.usage:
                usage = response_chunk.usage

        # TODO: we dont return all the fields, eg refusal
        response_message = ChatCompletionMessage(role="assistant")
        if response:
            response_message.content = response
        response_message.tool_calls = _get_formatted_tool_calls_response(
            tool_response_chunks
        )
        return ChatCompletion(
            id="id",
            choices=[
                Choice(
                    finish_reason="stop",
                    index=0,
                    message=response_message,
                )
            ],
            created=int(time.time()),
            model=request.model,
            object="chat.completion",
            usage=usage,
        )
    except NoAvailableNodesError:
        raise error_responses.NoAvailableInferenceNodesError()


def _get_formatted_tool_calls_response(
    tool_response_chunks: List[ChoiceDeltaToolCall],
) -> Optional[List[ChatCompletionMessageToolCall]]:
    if not tool_response_chunks:
        return None
    return convert_tool_call_chunks_to_non_streaming.execute(tool_response_chunks)
