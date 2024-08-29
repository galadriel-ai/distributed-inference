from typing import AsyncGenerator
from unittest.mock import MagicMock
from uuid import UUID

from openai.types.chat import ChatCompletionChunk
from openai.types.chat import ChatCompletionMessage
from openai.types.chat.chat_completion import Choice as CompletionChoice
from openai.types.chat.chat_completion_chunk import Choice
from openai.types.chat.chat_completion_chunk import ChoiceDelta

from distributedinference.domain.node.entities import InferenceResponse
from distributedinference.domain.user.entities import User
from distributedinference.service.completions import chat_completions_service as service
from distributedinference.service.completions.entities import ChatCompletion
from distributedinference.service.completions.entities import ChatCompletionRequest
from distributedinference.service.completions.entities import Message

USER_UUID = UUID("066d0263-61d3-76a4-8000-6b1403cac403")
USER = User(uid=USER_UUID, name="user", email="user@email.com")
MOCK_UUID = UUID("a2e3db51-7a7f-473c-8cd5-390e7ed1e1c7")


def setup():
    service.uuid7 = MagicMock()
    service.uuid7.return_value = MOCK_UUID

    service.run_inference_use_case = MagicMock()


class MockInference:
    def __init__(self, chunk_count: int):
        self.chunk_count = chunk_count

    async def mock_inference(
        self, *args, **kwargs
    ) -> AsyncGenerator[InferenceResponse, None]:
        for i in range(3):
            yield InferenceResponse(
                request_id=str(MOCK_UUID),
                chunk=ChatCompletionChunk(
                    id=f"mock-{i}",
                    choices=[
                        Choice(
                            delta=ChoiceDelta(
                                content=f"{i}",
                                role="assistant",
                            ),
                            index=0,
                            finish_reason=None,
                        )
                    ],
                    created=123,
                    model="llama3",
                    object="chat.completion.chunk",
                ),
            )
        yield InferenceResponse(
            request_id=str(MOCK_UUID),
            chunk=ChatCompletionChunk(
                id=f"mock-{self.chunk_count}",
                choices=[
                    Choice(
                        delta=ChoiceDelta(),
                        index=0,
                        finish_reason="stop",
                    )
                ],
                created=123,
                model="llama3",
                object="chat.completion.chunk",
            ),
        )


async def test_success():
    mock_inference = MockInference(chunk_count=3)
    service.time.time = MagicMock()
    service.time.time.return_value = 1337

    service.run_inference_use_case.execute = mock_inference.mock_inference
    res = await service.execute(
        USER,
        ChatCompletionRequest(
            model="llama3", messages=[Message(role="user", content="asd")]
        ),
        MagicMock(),
        MagicMock(),
    )
    assert res == ChatCompletion(
        id="id",
        choices=[
            CompletionChoice(
                finish_reason="stop",
                index=0,
                logprobs=None,
                message=ChatCompletionMessage(
                    content="012",
                    refusal=None,
                    role="assistant",
                    function_call=None,
                    tool_calls=None,
                ),
            )
        ],
        created=1337,
        model="llama3",
        object="chat.completion",
        service_tier=None,
        system_fingerprint=None,
        usage=None,
    )
