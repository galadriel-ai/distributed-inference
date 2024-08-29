import time

from openai.types.chat import ChatCompletionMessage
from openai.types.chat import CompletionCreateParams
from openai.types.chat.chat_completion import ChatCompletion
from openai.types.chat.chat_completion import Choice
from uuid_extensions import uuid7

from distributedinference.domain.node import run_inference_use_case
from distributedinference.domain.node.entities import InferenceRequest
from distributedinference.domain.node.exceptions import NoAvailableNodesError
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service import error_responses
from distributedinference.service.completions.entities import ChatCompletion
from distributedinference.service.completions.entities import ChatCompletionRequest


async def execute(
    request: ChatCompletionRequest, node_repository: NodeRepository
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
        async for chunk in run_inference_use_case.execute(
            inference_request, node_repository
        ):
            if chunk.error:
                raise error_responses.InferenceError(
                    chunk.error.status_code, chunk.error.message
                )
            if chunk.chunk and chunk.chunk.choices[0].delta.content:
                response += chunk.chunk.choices[0].delta.content
        return ChatCompletion(
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
        )
    except NoAvailableNodesError:
        raise error_responses.NoAvailableInferenceNodesError()
