import time
from uuid import uuid4
from typing import List

from openai.types.chat import ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion import ChatCompletion

from distributedinference.domain.node.entities import InferenceContent
from distributedinference.domain.node.entities import InferenceMessage
from distributedinference.domain.node.entities import InferenceRequest
from distributedinference.domain.node import run_inference_use_case
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.completions.entities import Message
from distributedinference.service.completions.entities import ChatCompletion
from distributedinference.service.completions.entities import ChatCompletionRequest


async def execute(request: ChatCompletionRequest, node_repository: NodeRepository) -> ChatCompletion:
    inference_request = InferenceRequest(
        id=str(uuid4()),
        model=request.model,
        messages=_to_inference_messages(request.messages)
    )
    response = ""
    async for chunk in run_inference_use_case.execute(inference_request, node_repository):
        response += chunk.content
    return ChatCompletion(
        id="id",
        choices=[Choice(
            finish_reason="stop",
            index=0,
            message=ChatCompletionMessage(
                content=response,
                role="assistant"
            )
        )],
        created=int(time.time()),
        model=request.model,
        object="chat.completion"
    )

def _to_inference_messages(messages: List[Message]) -> List[InferenceMessage]:
    return [
        InferenceMessage(
            role=message.role,
            content=InferenceContent(type="text", value=message.content),
        )
        for message in messages
    ]
