import json
from typing import AsyncGenerator
from unittest.mock import MagicMock
from uuid import UUID

from openai.types.chat import ChatCompletionChunk
from openai.types.chat.chat_completion_chunk import Choice
from openai.types.chat.chat_completion_chunk import ChoiceDelta

from distributedinference.domain.node.entities import InferenceResponse
from distributedinference.service.completions import chat_completions_stream_service as service
from distributedinference.service.completions.entities import ChatCompletionRequest
from distributedinference.service.completions.entities import Message

MOCK_UUID = UUID("a2e3db51-7a7f-473c-8cd5-390e7ed1e1c7")


def setup():
    service.uuid7 = MagicMock()
    service.uuid7.return_value = MOCK_UUID

    service.run_inference_use_case = MagicMock()


class MockInference:
    def __init__(self, chunk_count: int):
        self.chunk_count = chunk_count

    async def mock_inference(self, *args, **kwargs) -> AsyncGenerator[InferenceResponse, None]:
        for i in range(3):
            yield InferenceResponse(
                request_id=str(MOCK_UUID),
                chunk=ChatCompletionChunk(
                    id=f"mock-{i}",
                    choices=[Choice(
                        delta=ChoiceDelta(
                            content=f"{i}",
                            role="assistant",
                        ),
                        index=0,
                        finish_reason=None,
                    )],
                    created=123,
                    model="llama3",
                    object="chat.completion.chunk",
                )
            )
        yield InferenceResponse(
            request_id=str(MOCK_UUID),
            chunk=ChatCompletionChunk(
                id=f"mock-{self.chunk_count}",
                choices=[Choice(
                    delta=ChoiceDelta(),
                    index=0,
                    finish_reason="stop",
                )],
                created=123,
                model="llama3",
                object="chat.completion.chunk",
            )
        )


async def test_success():
    mock_inference = MockInference(chunk_count=3)

    service.run_inference_use_case.execute = mock_inference.mock_inference
    res = service.execute(
        ChatCompletionRequest(
            model="llama3",
            messages=[
                Message(
                    role="user",
                    content="asd"
                )
            ]
        ),
        MagicMock()
    )

    chunks = []
    content = ""
    async for chunk in res:
        chunks.append(chunk)
        try:
            parsed = json.loads(chunk.split("data: ")[1])
            c = parsed["choices"][0]["delta"].get("content")
            if c:
                content += c
        except:
            pass
    assert len(chunks) == 5
    assert content == "012"
    assert chunks[-1] == "data: [DONE]"
