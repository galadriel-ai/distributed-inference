import time
from typing import AsyncGenerator
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from uuid import UUID
from uuid import uuid1

import pytest
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletionChunk
from openai.types.chat.chat_completion_chunk import Choice
from openai.types.chat.chat_completion_chunk import ChoiceDelta
from packaging.version import Version

from distributedinference.domain.node import run_inference_use_case as use_case
from distributedinference.domain.node.entities import BackendHost, ConnectedNode
from distributedinference.domain.node.entities import InferenceError
from distributedinference.domain.node.entities import InferenceErrorStatusCodes
from distributedinference.domain.node.entities import InferenceRequest
from distributedinference.domain.node.entities import InferenceResponse
from distributedinference.domain.node.entities import InferenceStatusCodes
from distributedinference.domain.node.entities import NodeStatus
from distributedinference.domain.node.exceptions import NoAvailableNodesError
from distributedinference.repository.connected_node_repository import (
    ConnectedNodeRepository,
)
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.service.completions.entities import ChatCompletionRequest
from distributedinference.service.completions.entities import Message
from distributedinference.service.completions.entities import StreamOptions

USER_UUID = UUID("066d0263-61d3-76a4-8000-6b1403cac403")
API_KEY = "consumer-api-key"


@pytest.fixture
def mock_websocket():
    return MagicMock()


@pytest.fixture
def connected_node_factory(mock_websocket):
    def _create_node(uid, model="model", version="0.0.16"):
        return ConnectedNode(
            uid,
            uuid1(),
            model,
            16000,
            int(time.time()),
            BackendHost.from_value("distributed-inference-us"),
            mock_websocket,
            {},
            NodeStatus.RUNNING,
            version=Version(version),
        )

    return _create_node


TEST_NODE_ID = uuid1()
MOCK_UUID = uuid1()

INFERENCE_ERROR = InferenceError(
    status_code=InferenceErrorStatusCodes.BAD_REQUEST, message="mock error"
)

CHUNK_COUNT = 3
LAST_CHUNK = ChatCompletionChunk(
    id=f"mock-{CHUNK_COUNT}",
    choices=[],
    created=123,
    model="llama3",
    object="chat.completion.chunk",
    usage=CompletionUsage(
        prompt_tokens=10,
        completion_tokens=20,
        total_tokens=30,
    ),
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
                    usage=CompletionUsage(
                        prompt_tokens=10,
                        completion_tokens=20,
                        total_tokens=30,
                    ),
                ),
            )
        yield InferenceResponse(
            node_id=uuid1(),
            request_id=str(MOCK_UUID),
            chunk=LAST_CHUNK,
        )


class MockInferenceNoneResponse:
    async def mock_inference(
        self, *args, **kwargs
    ) -> AsyncGenerator[InferenceResponse, None]:
        yield None


class MockInferenceError:
    async def mock_inference(
        self, *args, **kwargs
    ) -> AsyncGenerator[InferenceResponse, None]:
        yield InferenceResponse(
            node_id=uuid1(),
            request_id=str(MOCK_UUID),
            error=INFERENCE_ERROR,
        )


def setup_function():
    use_case.is_node_performant = MagicMock()
    use_case.is_node_performant.execute.return_value = True

    use_case.select_node_use_case = MagicMock()


async def test_success(connected_node_factory):
    mock_node_repository = MagicMock(NodeRepository)
    mock_connected_node_repository = MagicMock(ConnectedNodeRepository)
    mock_tokens_repository = MagicMock(TokensRepository)

    use_case.select_node_use_case.execute.return_value = connected_node_factory(
        TEST_NODE_ID
    )

    mock_connected_node_repository.send_inference_request = AsyncMock()
    mock_connected_node_repository.receive_for_request = AsyncMock(
        side_effect=[
            InferenceResponse(
                node_id=TEST_NODE_ID,
                request_id="request_id",
                chunk=MagicMock(usage=None),
                error=None,
                status=InferenceStatusCodes.RUNNING,
            ),
            InferenceResponse(
                node_id=TEST_NODE_ID,
                request_id="request_id",
                chunk=MagicMock(choices=[MagicMock(finish_reason="stop")], usage=None),
                error=None,
                status=InferenceStatusCodes.RUNNING,
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
                status=InferenceStatusCodes.RUNNING,
            ),
            InferenceResponse(
                node_id=TEST_NODE_ID,
                request_id="request_id",
                chunk=None,
                error=None,
                status=InferenceStatusCodes.DONE,
            ),
        ]
    )
    mock_connected_node_repository.cleanup_request = AsyncMock()

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
        mock_node_repository,
        mock_connected_node_repository,
        mock_tokens_repository,
        AsyncMock(),
        AsyncMock(),
        MagicMock(),
    )
    async for response in executor.execute(
        USER_UUID,
        API_KEY,
        None,
        request,
    ):
        responses.append(response)

    assert len(responses) == 4
    assert responses[0].request_id == "request_id"
    assert responses[1].request_id == "request_id"
    assert responses[1].chunk.choices[0].finish_reason == "stop"
    mock_connected_node_repository.send_inference_request.assert_awaited_once_with(
        TEST_NODE_ID, request
    )
    mock_connected_node_repository.cleanup_request.assert_called_once_with(
        TEST_NODE_ID, "request_id"
    )


async def test_no_nodes_forward_to_peers():
    mock_node_repository = MagicMock(NodeRepository)
    mock_connected_node_repository = MagicMock(ConnectedNodeRepository)
    mock_tokens_repository = MagicMock(TokensRepository)
    use_case.select_node_use_case.execute.return_value = None

    mock_inference = MockInference()
    use_case.peer_nodes_forwarding = MagicMock()
    use_case.peer_nodes_forwarding.execute = mock_inference.mock_inference

    chat_input = await ChatCompletionRequest(
        model="llama3", messages=[Message(role="user", content="asd")]
    ).to_openai_chat_completion()
    request = InferenceRequest(
        id="request_id",
        model="model-1",
        chat_request=chat_input,
    )

    executor = use_case.InferenceExecutor(
        mock_node_repository,
        mock_connected_node_repository,
        mock_tokens_repository,
        AsyncMock(),
        AsyncMock(),
        MagicMock(),
    )
    result = []
    async for response in executor.execute(
        USER_UUID,
        API_KEY,
        None,
        request,
    ):
        result.append(response)

    assert len(result) == 4
    assert result[-1].chunk == LAST_CHUNK


async def test_no_nodes_forward_to_peers_failed():
    mock_node_repository = MagicMock(NodeRepository)
    mock_connected_node_repository = MagicMock(ConnectedNodeRepository)
    mock_tokens_repository = MagicMock(TokensRepository)
    use_case.select_node_use_case.execute.return_value = None

    mock_inference = MockInferenceError()
    use_case.peer_nodes_forwarding = MagicMock()
    use_case.peer_nodes_forwarding.execute = mock_inference.mock_inference

    chat_input = await ChatCompletionRequest(
        model="llama3", messages=[Message(role="user", content="asd")]
    ).to_openai_chat_completion()
    request = InferenceRequest(
        id="request_id",
        model="model-1",
        chat_request=chat_input,
    )

    executor = use_case.InferenceExecutor(
        mock_node_repository,
        mock_connected_node_repository,
        mock_tokens_repository,
        AsyncMock(),
        AsyncMock(),
        MagicMock(),
    )
    result = []
    async for request in executor.execute(
        USER_UUID,
        API_KEY,
        None,
        request,
    ):
        result.append(request)
    assert len(result) == 1
    assert result[0].error == INFERENCE_ERROR


async def test_no_nodes_no_forward_for_forwarding_request():
    mock_node_repository = MagicMock(NodeRepository)
    mock_connected_node_repository = MagicMock(ConnectedNodeRepository)
    mock_tokens_repository = MagicMock(TokensRepository)
    use_case.select_node_use_case.execute.return_value = None

    mock_inference = MockInference()
    use_case.peer_nodes_forwarding = MagicMock()
    use_case.peer_nodes_forwarding.execute = mock_inference.mock_inference

    chat_input = await ChatCompletionRequest(
        model="llama3", messages=[Message(role="user", content="asd")]
    ).to_openai_chat_completion()
    request = InferenceRequest(
        id="request_id",
        model="model-1",
        chat_request=chat_input,
    )

    executor = use_case.InferenceExecutor(
        mock_node_repository,
        mock_connected_node_repository,
        mock_tokens_repository,
        AsyncMock(),
        AsyncMock(),
        MagicMock(),
    )
    with pytest.raises(NoAvailableNodesError):
        async for response in executor.execute(
            USER_UUID,
            API_KEY,
            "distributed-inference-us",
            request,
        ):
            pass


# TODO: new test when no nodes and proxy also fails
async def test_no_nodes_uses_proxy():
    mock_node_repository = MagicMock(NodeRepository)
    mock_connected_node_repository = MagicMock(ConnectedNodeRepository)
    mock_tokens_repository = MagicMock(TokensRepository)
    use_case.select_node_use_case.execute.return_value = None

    mock_inference_none_response = MockInferenceNoneResponse()
    use_case.peer_nodes_forwarding = MagicMock()
    use_case.peer_nodes_forwarding.execute = mock_inference_none_response.mock_inference

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
        mock_node_repository,
        mock_connected_node_repository,
        mock_tokens_repository,
        AsyncMock(),
        AsyncMock(),
        MagicMock(),
    )
    result = []
    async for request in executor.execute(
        USER_UUID,
        API_KEY,
        None,
        request,
    ):
        result.append(request)
    assert len(result) == 4
    assert result[-1].chunk == LAST_CHUNK


async def test_no_nodes_and_proxy_also_fails():
    mock_node_repository = MagicMock(NodeRepository)
    mock_connected_node_repository = MagicMock(ConnectedNodeRepository)
    mock_tokens_repository = MagicMock(TokensRepository)
    use_case.select_node_use_case.execute.return_value = None

    mock_inference_none_response = MockInferenceNoneResponse()
    use_case.peer_nodes_forwarding = MagicMock()
    use_case.peer_nodes_forwarding.execute = mock_inference_none_response.mock_inference

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
        mock_node_repository,
        mock_connected_node_repository,
        mock_tokens_repository,
        AsyncMock(),
        AsyncMock(),
        MagicMock(),
    )
    result = []
    async for request in executor.execute(
        USER_UUID,
        API_KEY,
        None,
        request,
    ):
        result.append(request)
    assert len(result) == 1
    assert result[0].error == INFERENCE_ERROR


async def test_streaming_no_usage(connected_node_factory):
    mock_node_repository = MagicMock(NodeRepository)
    mock_connected_node_repository = MagicMock(ConnectedNodeRepository)
    mock_tokens_repository = MagicMock(TokensRepository)
    use_case.select_node_use_case.execute.return_value = connected_node_factory(
        TEST_NODE_ID
    )

    mock_connected_node_repository.send_inference_request = AsyncMock()
    mock_connected_node_repository.receive_for_request = AsyncMock(
        side_effect=[
            InferenceResponse(
                node_id=TEST_NODE_ID,
                request_id="request_id",
                chunk=MagicMock(choices=[MagicMock(finish_reason=None)], usage=None),
                error=None,
                status=InferenceStatusCodes.RUNNING,
            ),
            InferenceResponse(
                node_id=TEST_NODE_ID,
                request_id="request_id",
                chunk=MagicMock(choices=[MagicMock(finish_reason="stop")], usage=None),
                error=None,
                status=InferenceStatusCodes.RUNNING,
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
                status=InferenceStatusCodes.RUNNING,
            ),
            InferenceResponse(
                node_id=TEST_NODE_ID,
                request_id="request_id",
                chunk=None,
                error=None,
                status=InferenceStatusCodes.DONE,
            ),
        ]
    )
    mock_connected_node_repository.cleanup_request = AsyncMock()

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
        mock_node_repository,
        mock_connected_node_repository,
        mock_tokens_repository,
        AsyncMock(),
        AsyncMock(),
        MagicMock(),
    )
    async for response in executor.execute(
        USER_UUID,
        API_KEY,
        None,
        request,
    ):
        responses.append(response)

    assert len(responses) == 4
    assert responses[0].request_id == "request_id"
    assert responses[1].request_id == "request_id"
    assert responses[1].chunk.choices[0].finish_reason == "stop"
    assert responses[2].request_id == "request_id"
    assert responses[2].chunk.choices == []
    assert responses[2].chunk.usage is None

    mock_connected_node_repository.send_inference_request.assert_awaited_once_with(
        TEST_NODE_ID, request
    )
    mock_connected_node_repository.cleanup_request.assert_called_once_with(
        TEST_NODE_ID, "request_id"
    )


async def test_streaming_usage_includes_extra_chunk(connected_node_factory):
    mock_node_repository = MagicMock(NodeRepository)
    mock_connected_node_repository = MagicMock(ConnectedNodeRepository)
    mock_tokens_repository = MagicMock(TokensRepository)
    use_case.select_node_use_case.execute.return_value = connected_node_factory(
        TEST_NODE_ID
    )

    mock_connected_node_repository.send_inference_request = AsyncMock()
    mock_connected_node_repository.receive_for_request = AsyncMock(
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
            InferenceResponse(
                node_id=TEST_NODE_ID,
                request_id="request_id",
                chunk=None,
                error=None,
                status=InferenceStatusCodes.DONE,
            ),
        ]
    )
    mock_connected_node_repository.cleanup_request = AsyncMock()

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
        mock_node_repository,
        mock_connected_node_repository,
        mock_tokens_repository,
        AsyncMock(),
        AsyncMock(),
        MagicMock(),
    )
    async for response in executor.execute(
        USER_UUID,
        None,
        API_KEY,
        request,
    ):
        responses.append(response)

    # 3 content chunks, 1 extra chunk for usage
    assert len(responses) == 4
    assert responses[0].request_id == "request_id"
    assert responses[1].request_id == "request_id"
    assert responses[1].chunk.choices[0].finish_reason == "stop"
    mock_connected_node_repository.send_inference_request.assert_awaited_once_with(
        TEST_NODE_ID, request
    )
    mock_connected_node_repository.cleanup_request.assert_called_once_with(
        TEST_NODE_ID, "request_id"
    )


async def test_old_node_still_works(connected_node_factory):
    mock_node_repository = MagicMock(NodeRepository)
    mock_connected_node_repository = MagicMock(ConnectedNodeRepository)
    mock_tokens_repository = MagicMock(TokensRepository)
    use_case.select_node_use_case.execute.return_value = connected_node_factory(
        TEST_NODE_ID, version="0.0.15"
    )

    node = connected_node_factory(TEST_NODE_ID, "0.0.15")
    mock_connected_node_repository.send_inference_request = AsyncMock()
    mock_connected_node_repository.receive_for_request = AsyncMock(
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
    mock_connected_node_repository.cleanup_request = AsyncMock()

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
        mock_node_repository,
        mock_connected_node_repository,
        mock_tokens_repository,
        AsyncMock(),
        AsyncMock(),
        MagicMock(),
    )
    async for response in executor.execute(
        USER_UUID,
        API_KEY,
        None,
        request,
    ):
        responses.append(response)

    # 2 content chunk, 1 stop chunk
    assert len(responses) == 3
    assert responses[0].request_id == "request_id"
    assert responses[1].request_id == "request_id"
    assert responses[1].chunk.choices[0].finish_reason == "stop"
    assert responses[2].request_id == "request_id"
    assert responses[2].chunk.choices == []
    assert responses[2].chunk.usage is not None

    mock_connected_node_repository.send_inference_request.assert_awaited_once_with(
        TEST_NODE_ID, request
    )
    mock_connected_node_repository.cleanup_request.assert_called_once_with(
        TEST_NODE_ID, "request_id"
    )


async def test_inference_error_stops_loop(connected_node_factory):
    mock_node_repository = MagicMock(NodeRepository)
    mock_connected_node_repository = MagicMock(ConnectedNodeRepository)
    mock_tokens_repository = MagicMock(TokensRepository)
    use_case.select_node_use_case.execute.return_value = connected_node_factory(
        TEST_NODE_ID
    )

    mock_connected_node_repository.send_inference_request = AsyncMock()
    mock_connected_node_repository.receive_for_request = AsyncMock(
        side_effect=[
            InferenceResponse(
                node_id=TEST_NODE_ID,
                request_id="request_id",
                chunk=None,
                error=InferenceError(
                    status_code=InferenceErrorStatusCodes.NOT_FOUND,
                    message="No model found",
                ),
            ),
        ]
    )
    mock_connected_node_repository.cleanup_request = AsyncMock()

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
        mock_node_repository,
        mock_connected_node_repository,
        mock_tokens_repository,
        AsyncMock(),
        AsyncMock(),
        MagicMock(),
    )
    async for response in executor.execute(
        USER_UUID,
        None,
        API_KEY,
        request,
    ):
        responses.append(response)

    # 1 error response
    assert len(responses) == 1
    assert responses[0].request_id == "request_id"
    assert responses[0].chunk == None
    assert responses[0].error.status_code == InferenceErrorStatusCodes.NOT_FOUND
    assert responses[0].error.message == "No model found"
    mock_connected_node_repository.send_inference_request.assert_awaited_once_with(
        TEST_NODE_ID, request
    )
    mock_connected_node_repository.cleanup_request.assert_called_once_with(
        TEST_NODE_ID, "request_id"
    )


async def test_inference_error_marks_node_as_unhealthy(connected_node_factory):
    mock_node_repository = MagicMock(NodeRepository)
    mock_connected_node_repository = MagicMock(ConnectedNodeRepository)
    mock_tokens_repository = MagicMock(TokensRepository)
    use_case.select_node_use_case.execute.return_value = connected_node_factory(
        TEST_NODE_ID
    )

    mock_connected_node_repository.send_inference_request = AsyncMock()
    mock_connected_node_repository.receive_for_request = AsyncMock(
        side_effect=[
            InferenceResponse(
                node_id=TEST_NODE_ID,
                request_id="request_id",
                chunk=None,
                error=InferenceError(
                    status_code=InferenceErrorStatusCodes.NOT_FOUND,
                    message="No model found",
                ),
            ),
        ]
    )
    mock_connected_node_repository.cleanup_request = AsyncMock()
    mock_node_repository.update_node_status = AsyncMock()
    mock_node_repository.get_node_status = AsyncMock(return_value=NodeStatus.RUNNING)

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
        mock_node_repository,
        mock_connected_node_repository,
        mock_tokens_repository,
        AsyncMock(),
        AsyncMock(),
        MagicMock(),
    )
    async for response in executor.execute(
        USER_UUID,
        API_KEY,
        None,
        request,
    ):
        responses.append(response)

    # 1 error response
    assert len(responses) == 1
    assert responses[0].request_id == "request_id"
    assert responses[0].chunk == None
    assert responses[0].error.status_code == InferenceErrorStatusCodes.NOT_FOUND
    assert responses[0].error.message == "No model found"
    mock_connected_node_repository.send_inference_request.assert_awaited_once_with(
        TEST_NODE_ID, request
    )
    mock_connected_node_repository.cleanup_request.assert_called_once_with(
        TEST_NODE_ID, "request_id"
    )
    mock_node_repository.update_node_status.assert_awaited_once_with(
        TEST_NODE_ID, NodeStatus.RUNNING_DEGRADED
    )


async def test_inference_client_error_not_marks_node_as_unhealthy(
    connected_node_factory,
):
    mock_node_repository = MagicMock(NodeRepository)
    mock_connected_node_repository = MagicMock(ConnectedNodeRepository)
    mock_tokens_repository = MagicMock(TokensRepository)
    use_case.select_node_use_case.execute.return_value = connected_node_factory(
        TEST_NODE_ID
    )

    mock_connected_node_repository.send_inference_request = AsyncMock()
    mock_connected_node_repository.receive_for_request = AsyncMock(
        side_effect=[
            InferenceResponse(
                node_id=TEST_NODE_ID,
                request_id="request_id",
                chunk=None,
                error=InferenceError(
                    status_code=InferenceErrorStatusCodes.BAD_REQUEST,
                    message="Client error",
                ),
            ),
        ]
    )
    mock_connected_node_repository.cleanup_request = AsyncMock()
    mock_node_repository.update_node_status = AsyncMock()
    mock_node_repository.get_node_status = AsyncMock(return_value=NodeStatus.RUNNING)

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
        mock_node_repository,
        mock_connected_node_repository,
        mock_tokens_repository,
        AsyncMock(),
        AsyncMock(),
        MagicMock(),
    )
    async for response in executor.execute(
        USER_UUID,
        None,
        API_KEY,
        request,
    ):
        responses.append(response)

    # 1 error response
    assert len(responses) == 1
    assert responses[0].request_id == "request_id"
    assert responses[0].chunk == None
    assert responses[0].error.status_code == InferenceErrorStatusCodes.BAD_REQUEST
    assert responses[0].error.message == "Client error"
    mock_connected_node_repository.send_inference_request.assert_awaited_once_with(
        TEST_NODE_ID, request
    )
    mock_connected_node_repository.cleanup_request.assert_called_once_with(
        TEST_NODE_ID, "request_id"
    )
    # Node status MUST not be updated if it's a client side error
    mock_node_repository.update_node_status.assert_not_called()
