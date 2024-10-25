from typing import AsyncGenerator
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import UUID, uuid1

from openai.types import CompletionUsage
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
USER = User(
    uid=USER_UUID,
    name="user",
    email="user@email.com",
    usage_tier_id=UUID("06706644-2409-7efd-8000-3371c5d632d3"),
)
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
                node_id=uuid1(),
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
            node_id=uuid1(),
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
        yield InferenceResponse(
            node_id=uuid1(),
            request_id=str(MOCK_UUID),
            chunk=ChatCompletionChunk(
                id=f"mock-{self.chunk_count}",
                choices=[],
                created=123,
                model="llama3",
                object="chat.completion.chunk",
                usage=CompletionUsage(
                    completion_tokens=10,
                    prompt_tokens=20,
                    total_tokens=30,
                ),
            ),
        )


async def test_success():
    mock_inference = MockInference(chunk_count=3)
    service.time.time = MagicMock()
    service.time.time.return_value = 1337

    with patch.object(
        service, 'InferenceExecutor',
        return_value=MagicMock(execute=mock_inference.mock_inference)
    ):
        res = await service.execute(
            USER,
            ChatCompletionRequest(
                model="llama3", messages=[Message(role="user", content="asd")]
            ),
            MagicMock(),
            MagicMock(),
            AsyncMock(),
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
            usage=CompletionUsage(
                completion_tokens=10,
                prompt_tokens=20,
                total_tokens=30,
            ),
        )


