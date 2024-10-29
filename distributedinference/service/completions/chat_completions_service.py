import time

from openai.types.chat import ChatCompletionMessage
from openai.types.chat import CompletionCreateParams
from openai.types.chat.chat_completion import Choice
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
from distributedinference.service.completions.entities import ChatCompletion
from distributedinference.service.completions.entities import ChatCompletionRequest
from distributedinference.utils.timer import async_timer

logger = api_logger.get()


# pylint: disable=R0913
@async_timer("chat_completions_service.execute", logger=logger)
async def execute(
    user: User,
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
            request=inference_request,
        ):
            if inference_response.error:
                raise error_responses.InferenceError(
                    node_id=inference_response.node_id,
                    status_code=inference_response.error.status_code,
                    message_extra=inference_response.error.message,
                )
            if (
                inference_response.chunk
                and inference_response.chunk.choices
                and inference_response.chunk.choices[0].delta.content
            ):
                response += inference_response.chunk.choices[0].delta.content
            if inference_response.chunk and inference_response.chunk.usage:
                usage = inference_response.chunk.usage
        chat_completion = ChatCompletion(
            id="id",
            choices=[
                Choice(
                    finish_reason="stop",
                    index=0,
                    message=ChatCompletionMessage(content=response, role="assistant"),
                )
            ],
            created=int(time.time()),
            model=request.model,
            object="chat.completion",
            usage=usage,
        )
        return chat_completion
    except NoAvailableNodesError:
        raise error_responses.NoAvailableInferenceNodesError()
