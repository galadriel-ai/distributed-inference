import time
from typing import AsyncGenerator
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from uuid import UUID, uuid1

import pytest
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletionChunk
from openai.types.chat.chat_completion_chunk import Choice
from openai.types.chat.chat_completion_chunk import ChoiceDelta

import settings
from distributedinference.domain.node import run_inference_use_case as use_case
from distributedinference.domain.node.entities import ConnectedNode
from distributedinference.domain.node.entities import InferenceError
from distributedinference.domain.node.entities import InferenceStatusCodes
from distributedinference.domain.node.entities import InferenceRequest
from distributedinference.domain.node.entities import InferenceResponse
from distributedinference.domain.node.exceptions import NoAvailableNodesError
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.service.completions.entities import ChatCompletionRequest
from distributedinference.service.completions.entities import Message
from distributedinference.service.completions.entities import StreamOptions

USER_UUID = UUID("066d0263-61d3-76a4-8000-6b1403cac403")


@pytest.fixture
def mock_websocket():
    return MagicMock()


@pytest.fixture
def connected_node_factory(mock_websocket):
    def _create_node(uid, model="model"):
        return ConnectedNode(
            uid, uuid1(), model, 16000, int(time.time()), mock_websocket, {}
        )

    return _create_node


TEST_NODE_ID = uuid1()
MOCK_UUID = uuid1()

CHUNK_COUNT = 3
LAST_CHUNK = ChatCompletionChunk(
    id=f"mock-{CHUNK_COUNT}",
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
)


class MockInference:

    async def mock_inference(
        self, *args, **kwargs
    ) -> AsyncGenerator[InferenceResponse, None]:
        for i in range(CHUNK_COUNT):
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
            chunk=LAST_CHUNK,
        )


class MockInferenceError:
    async def mock_inference(
        self, *args, **kwargs
    ) -> AsyncGenerator[InferenceResponse, None]:
        yield InferenceResponse(
            node_id=uuid1(),
            request_id=str(MOCK_UUID),
            error=InferenceError(
                status_code=InferenceStatusCodes.BAD_REQUEST, message="mock error"
            ),
        )


async def test_success(connected_node_factory):
    mock_node_repository = MagicMock(NodeRepository)
    mock_tokens_repository = MagicMock(TokensRepository)

    mock_node_repository.select_node = MagicMock(
        return_value=connected_node_factory(TEST_NODE_ID)
    )
    mock_node_repository.send_inference_request = AsyncMock()
    mock_node_repository.receive_for_request = AsyncMock(
        side_effect=[
            InferenceResponse(
                node_id=TEST_NODE_ID,
                request_id="request_id",
                chunk=MagicMock(usage=None),
                error=None,
            ),
            InferenceResponse(
                node_id=TEST_NODE_ID,
                request_id="request_id",
                chunk=MagicMock(choices=[MagicMock(finish_reason="stop")], usage=None),
                error=None,
            ),
            InferenceResponse(
                node_id=TEST_NODE_ID,
                request_id="request_id",
                chunk=MagicMock(
                    choices=[],
                    usage=CompletionUsage(
                        prompt_tokens=10, completion_tokens=20, total_tokens=30
                    ),
                ),
                error=None,
            ),
        ]
    )
    mock_node_repository.cleanup_request = AsyncMock()

    chat_input = await ChatCompletionRequest(
        model="llama3", messages=[Message(role="user", content="asd")]
    ).to_openai_chat_completion()
    request = InferenceRequest(
        id="request_id",
        model="model-1",
        chat_request=chat_input,
    )

    responses = []
    executor = use_case.InferenceExecutor(
        mock_node_repository, mock_tokens_repository, AsyncMock(), MagicMock()
    )
    async for response in executor.execute(
        USER_UUID,
        request,
    ):
        responses.append(response)

    assert len(responses) == 3
    assert responses[0].request_id == "request_id"
    assert responses[1].request_id == "request_id"
    assert responses[1].chunk.choices[0].finish_reason == "stop"
    mock_node_repository.send_inference_request.assert_awaited_once_with(
        TEST_NODE_ID, request
    )
    mock_node_repository.cleanup_request.assert_awaited_once_with(
        TEST_NODE_ID, "request_id"
    )


# TODO: new test when no nodes and proxy also fails
async def test_no_nodes_uses_proxy():
    mock_node_repository = MagicMock(NodeRepository)
    mock_tokens_repository = MagicMock(TokensRepository)
    mock_node_repository.select_node = MagicMock(return_value=None)

    mock_inference = MockInference()
    use_case.llm_inference_proxy = MagicMock()
    use_case.llm_inference_proxy.execute = mock_inference.mock_inference

    chat_input = await ChatCompletionRequest(
        model="llama3", messages=[Message(role="user", content="asd")]
    ).to_openai_chat_completion()
    request = InferenceRequest(
        id="request_id",
        model="model-1",
        chat_request=chat_input,
    )

    executor = use_case.InferenceExecutor(
        mock_node_repository, mock_tokens_repository, AsyncMock(), MagicMock()
    )
    result = []
    async for request in executor.execute(
        USER_UUID,
        request,
    ):
        result.append(request)
    assert len(result) == 4
    assert result[-1].chunk == LAST_CHUNK


async def test_no_nodes_and_proxy_also_fails():
    mock_node_repository = MagicMock(NodeRepository)
    mock_tokens_repository = MagicMock(TokensRepository)
    mock_node_repository.select_node = MagicMock(return_value=None)

    mock_inference = MockInferenceError()
    use_case.llm_inference_proxy = MagicMock()
    use_case.llm_inference_proxy.execute = mock_inference.mock_inference

    chat_input = await ChatCompletionRequest(
        model="llama3", messages=[Message(role="user", content="asd")]
    ).to_openai_chat_completion()
    request = InferenceRequest(
        id="request_id",
        model="model-1",
        chat_request=chat_input,
    )

    executor = use_case.InferenceExecutor(
        mock_node_repository, mock_tokens_repository, AsyncMock(), MagicMock()
    )
    with pytest.raises(NoAvailableNodesError):
        async for _ in executor.execute(
            USER_UUID,
            request,
        ):
            pass


async def test_streaming_no_usage(connected_node_factory):
    mock_node_repository = MagicMock(NodeRepository)
    mock_tokens_repository = MagicMock(TokensRepository)
    mock_node_repository.select_node = MagicMock(
        return_value=connected_node_factory(TEST_NODE_ID)
    )
    mock_node_repository.send_inference_request = AsyncMock()
    mock_node_repository.receive_for_request = AsyncMock(
        side_effect=[
            InferenceResponse(
                node_id=TEST_NODE_ID,
                request_id="request_id",
                chunk=MagicMock(choices=[MagicMock(finish_reason=None)], usage=None),
                error=None,
            ),
            InferenceResponse(
                node_id=TEST_NODE_ID,
                request_id="request_id",
                chunk=MagicMock(choices=[MagicMock(finish_reason="stop")], usage=None),
                error=None,
            ),
            InferenceResponse(
                node_id=TEST_NODE_ID,
                request_id="request_id",
                chunk=MagicMock(
                    choices=[],
                    usage=CompletionUsage(
                        prompt_tokens=10, completion_tokens=20, total_tokens=30
                    ),
                ),
                error=None,
            ),
        ]
    )
    mock_node_repository.cleanup_request = AsyncMock()

    chat_input = await ChatCompletionRequest(
        model="llama3",
        messages=[
            Message(role="user", content="asd"),
        ],
        stream=True,
    ).to_openai_chat_completion()
    request = InferenceRequest(
        id="request_id",
        model="model-1",
        chat_request=chat_input,
    )

    responses = []
    executor = use_case.InferenceExecutor(
        mock_node_repository, mock_tokens_repository, AsyncMock(), MagicMock()
    )
    async for response in executor.execute(
        USER_UUID,
        request,
    ):
        responses.append(response)

    assert len(responses) == 2
    assert responses[0].request_id == "request_id"
    assert responses[1].request_id == "request_id"
    assert responses[1].chunk.choices[0].finish_reason == "stop"
    mock_node_repository.send_inference_request.assert_awaited_once_with(
        TEST_NODE_ID, request
    )
    mock_node_repository.cleanup_request.assert_awaited_once_with(
        TEST_NODE_ID, "request_id"
    )


async def test_streaming_usage_includes_extra_chunk(connected_node_factory):
    mock_node_repository = MagicMock(NodeRepository)
    mock_tokens_repository = MagicMock(TokensRepository)
    mock_node_repository.select_node = MagicMock(
        return_value=connected_node_factory(TEST_NODE_ID)
    )
    mock_node_repository.send_inference_request = AsyncMock()
    mock_node_repository.receive_for_request = AsyncMock(
        side_effect=[
            InferenceResponse(
                node_id=TEST_NODE_ID,
                request_id="request_id",
                chunk=MagicMock(choices=[MagicMock(finish_reason=None)], usage=None),
                error=None,
            ),
            InferenceResponse(
                node_id=TEST_NODE_ID,
                request_id="request_id",
                chunk=MagicMock(choices=[MagicMock(finish_reason="stop")], usage=None),
                error=None,
            ),
            InferenceResponse(
                node_id=TEST_NODE_ID,
                request_id="request_id",
                chunk=MagicMock(
                    choices=[],
                    usage=CompletionUsage(
                        prompt_tokens=10, completion_tokens=20, total_tokens=30
                    ),
                ),
                error=None,
            ),
        ]
    )
    mock_node_repository.cleanup_request = AsyncMock()

    chat_input = await ChatCompletionRequest(
        model="llama3",
        messages=[Message(role="user", content="asd")],
        stream=True,
        stream_options=StreamOptions(include_usage=True),
    ).to_openai_chat_completion()
    request = InferenceRequest(
        id="request_id",
        model="model-1",
        chat_request=chat_input,
    )

    responses = []
    executor = use_case.InferenceExecutor(
        mock_node_repository, mock_tokens_repository, AsyncMock(), MagicMock()
    )
    async for response in executor.execute(
        USER_UUID,
        request,
    ):
        responses.append(response)

    # 2 content chunks, 1 extra chunk for usage
    assert len(responses) == 3
    assert responses[0].request_id == "request_id"
    assert responses[1].request_id == "request_id"
    assert responses[1].chunk.choices[0].finish_reason == "stop"
    mock_node_repository.send_inference_request.assert_awaited_once_with(
        TEST_NODE_ID, request
    )
    mock_node_repository.cleanup_request.assert_awaited_once_with(
        TEST_NODE_ID, "request_id"
    )


async def test_inference_error_stops_loop(connected_node_factory):
    mock_node_repository = MagicMock(NodeRepository)
    mock_tokens_repository = MagicMock(TokensRepository)
    mock_node_repository.select_node = MagicMock(
        return_value=connected_node_factory(TEST_NODE_ID)
    )
    mock_node_repository.send_inference_request = AsyncMock()
    mock_node_repository.receive_for_request = AsyncMock(
        side_effect=[
            InferenceResponse(
                node_id=TEST_NODE_ID,
                request_id="request_id",
                chunk=None,
                error=InferenceError(
                    status_code=InferenceStatusCodes.NOT_FOUND, message="No model found"
                ),
            ),
        ]
    )
    mock_node_repository.cleanup_request = AsyncMock()

    chat_input = await ChatCompletionRequest(
        model="llama3",
        messages=[Message(role="user", content="asd")],
        stream=True,
        stream_options=StreamOptions(include_usage=True),
    ).to_openai_chat_completion()
    request = InferenceRequest(
        id="request_id",
        model="model-1",
        chat_request=chat_input,
    )

    responses = []
    executor = use_case.InferenceExecutor(
        mock_node_repository, mock_tokens_repository, AsyncMock(), MagicMock()
    )
    async for response in executor.execute(
        USER_UUID,
        request,
    ):
        responses.append(response)

    # 1 error response
    assert len(responses) == 1
    assert responses[0].request_id == "request_id"
    assert responses[0].chunk == None
    assert responses[0].error.status_code == InferenceStatusCodes.NOT_FOUND
    assert responses[0].error.message == "No model found"
    mock_node_repository.send_inference_request.assert_awaited_once_with(
        TEST_NODE_ID, request
    )
    mock_node_repository.cleanup_request.assert_awaited_once_with(
        TEST_NODE_ID, "request_id"
    )


async def test_inference_error_marks_node_as_unhealthy(connected_node_factory):
    mock_node_repository = MagicMock(NodeRepository)
    mock_tokens_repository = MagicMock(TokensRepository)
    mock_node_repository.select_node = MagicMock(
        return_value=connected_node_factory(TEST_NODE_ID)
    )
    mock_node_repository.send_inference_request = AsyncMock()
    mock_node_repository.receive_for_request = AsyncMock(
        side_effect=[
            InferenceResponse(
                node_id=TEST_NODE_ID,
                request_id="request_id",
                chunk=None,
                error=InferenceError(
                    status_code=InferenceStatusCodes.NOT_FOUND, message="No model found"
                ),
            ),
        ]
    )
    mock_node_repository.cleanup_request = AsyncMock()
    mock_node_repository.update_node_health_status = AsyncMock()

    chat_input = await ChatCompletionRequest(
        model="llama3",
        messages=[Message(role="user", content="asd")],
        stream=True,
        stream_options=StreamOptions(include_usage=True),
    ).to_openai_chat_completion()
    request = InferenceRequest(
        id="request_id",
        model="model-1",
        chat_request=chat_input,
    )

    responses = []
    executor = use_case.InferenceExecutor(
        mock_node_repository, mock_tokens_repository, AsyncMock(), MagicMock()
    )
    async for response in executor.execute(
        USER_UUID,
        request,
    ):
        responses.append(response)

    # 1 error response
    assert len(responses) == 1
    assert responses[0].request_id == "request_id"
    assert responses[0].chunk == None
    assert responses[0].error.status_code == InferenceStatusCodes.NOT_FOUND
    assert responses[0].error.message == "No model found"
    mock_node_repository.send_inference_request.assert_awaited_once_with(
        TEST_NODE_ID, request
    )
    mock_node_repository.cleanup_request.assert_awaited_once_with(
        TEST_NODE_ID, "request_id"
    )
    mock_node_repository.update_node_health_status.assert_awaited_once_with(
        TEST_NODE_ID, False
    )
