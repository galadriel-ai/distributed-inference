from typing import AsyncIterable, Optional

from openai.types.chat import CompletionCreateParams
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
from distributedinference.repository.tokens_queue_repository import (
    TokensQueueRepository,
)
from distributedinference.service import error_responses
from distributedinference.service.completions.entities import ChatCompletionRequest

logger = api_logger.get()


# pylint: disable=R0801, R0913
async def execute(
    user: User,
    forwarding_from: Optional[str],
    request: ChatCompletionRequest,
    node_repository: NodeRepository,
    tokens_repository: TokensRepository,
    metrics_queue_repository: MetricsQueueRepository,
    tokens_queue_repository: TokensQueueRepository,
    analytics: Analytics,
) -> AsyncIterable:
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
        executor = InferenceExecutor(
            node_repository=node_repository,
            tokens_repository=tokens_repository,
            metrics_queue_repository=metrics_queue_repository,
            tokens_queue_repository=tokens_queue_repository,
            analytics=analytics,
        )
        async for inference_response in executor.execute(
            user_uid=user.uid,
            api_key=user.currently_using_api_key or "",
            forwarding_from=forwarding_from,
            request=inference_request,
        ):
            if inference_response.error:
                logger.error(
                    f"Inference error: "
                    f"node_id={inference_response.node_id}, "
                    f"status_code={inference_response.error.status_code}, "
                    f"message={inference_response.error.message}"
                )

                raise error_responses.InferenceError(
                    status_code=inference_response.error.status_code.value,
                    message_extra=inference_response.error.message,
                )
            if inference_response.chunk:
                yield f"data: {inference_response.chunk.to_json(indent=None)}\n\n"
            # TODO: what if chunk.chunk is None?
        yield "data: [DONE]"
    except NoAvailableNodesError:
        raise error_responses.NoAvailableInferenceNodesError()
