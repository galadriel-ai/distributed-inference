from typing import AsyncIterable
from typing import List

from uuid_extensions import uuid7

from distributedinference.domain.node import run_inference_use_case
from distributedinference.domain.node.entities import InferenceContent
from distributedinference.domain.node.entities import InferenceMessage
from distributedinference.domain.node.entities import InferenceRequest
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.completions.entities import ChatCompletionRequest
from distributedinference.service.completions.entities import Message


async def execute(
    request: ChatCompletionRequest, node_repository: NodeRepository
) -> AsyncIterable:
    inference_request = InferenceRequest(
        id=str(uuid7()),
        model=request.model,
        messages=_to_inference_messages(request.messages),
    )
    async for chunk in run_inference_use_case.execute(
        inference_request, node_repository
    ):
        yield f"data: {chunk.chunk.to_json(indent=None)}\n\n"
    yield "data: [DONE]"


def _to_inference_messages(messages: List[Message]) -> List[InferenceMessage]:
    return [
        InferenceMessage(
            role=message.role,
            content=InferenceContent(type="text", value=message.content),
        )
        for message in messages
    ]
