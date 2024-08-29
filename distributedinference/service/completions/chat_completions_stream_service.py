from typing import AsyncIterable

from openai.types.chat import CompletionCreateParams
from uuid_extensions import uuid7

from distributedinference.domain.node import run_inference_use_case
from distributedinference.domain.node.entities import InferenceRequest
from distributedinference.domain.node.exceptions import NoAvailableNodesError
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service import error_responses
from distributedinference.service.completions.entities import ChatCompletionRequest


async def execute(
    request: ChatCompletionRequest, node_repository: NodeRepository
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
        async for chunk in run_inference_use_case.execute(
            inference_request, node_repository
        ):
            if chunk.error:
                raise error_responses.InferenceError(
                    chunk.error.status_code, chunk.error.message
                )
            yield f"data: {chunk.chunk.to_json(indent=None)}\n\n"
        yield "data: [DONE]"
    except NoAvailableNodesError:
        raise error_responses.NoAvailableInferenceNodesError()
