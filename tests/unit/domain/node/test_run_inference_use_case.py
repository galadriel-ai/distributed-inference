import time
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from distributedinference.domain.node import run_inference_use_case as use_case
from distributedinference.domain.node.entities import ConnectedNode
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
            uid, model, int(time.time()), mock_websocket, {}
        )

    return _create_node


async def test_success(connected_node_factory):
    mock_node_repository = MagicMock(NodeRepository)
    mock_tokens_repository = MagicMock(TokensRepository)
    mock_node_repository.select_node = MagicMock(
        return_value=connected_node_factory("1")
    )
    mock_node_repository.send_inference_request = AsyncMock()
    mock_node_repository.receive_for_request = AsyncMock(
        side_effect=[
            InferenceResponse(
                request_id="request_id",
                chunk=MagicMock(usage=None),
                error=None,
            ),
            InferenceResponse(
                request_id="request_id",
                chunk=MagicMock(choices=[MagicMock(finish_reason="stop")], usage=None),
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
    async for response in use_case.execute(
        USER_UUID, request, mock_node_repository, mock_tokens_repository, AsyncMock()
    ):
        responses.append(response)

    assert len(responses) == 2
    assert responses[0].request_id == "request_id"
    assert responses[1].request_id == "request_id"
    assert responses[1].chunk.choices[0].finish_reason == "stop"
    mock_node_repository.send_inference_request.assert_awaited_once_with("1", request)
    mock_node_repository.cleanup_request.assert_awaited_once_with("1", "request_id")


async def test_no_nodes():
    mock_node_repository = MagicMock(NodeRepository)
    mock_tokens_repository = MagicMock(TokensRepository)
    mock_node_repository.select_node = MagicMock(return_value=None)

    chat_input = await ChatCompletionRequest(
        model="llama3", messages=[Message(role="user", content="asd")]
    ).to_openai_chat_completion()
    request = InferenceRequest(
        id="request_id",
        model="model-1",
        chat_request=chat_input,
    )

    with pytest.raises(NoAvailableNodesError):
        async for response in use_case.execute(
            USER_UUID, request, mock_node_repository, mock_tokens_repository, AsyncMock()
        ):
            pass


async def test_streaming_no_usage(connected_node_factory):
    mock_node_repository = MagicMock(NodeRepository)
    mock_tokens_repository = MagicMock(TokensRepository)
    mock_node_repository.select_node = MagicMock(
        return_value=connected_node_factory("1")
    )
    mock_node_repository.send_inference_request = AsyncMock()
    mock_node_repository.receive_for_request = AsyncMock(
        side_effect=[
            InferenceResponse(
                request_id="request_id",
                chunk=MagicMock(choices=[MagicMock(finish_reason=None)], usage=None),
                error=None,
            ),
            InferenceResponse(
                request_id="request_id",
                chunk=MagicMock(choices=[MagicMock(finish_reason="stop")], usage=None),
                error=None,
            ),
            InferenceResponse(
                request_id="request_id",
                chunk=MagicMock(choices=[], usage=None),
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
    async for response in use_case.execute(
        USER_UUID, request, mock_node_repository, mock_tokens_repository, AsyncMock()
    ):
        responses.append(response)

    assert len(responses) == 2
    assert responses[0].request_id == "request_id"
    assert responses[1].request_id == "request_id"
    assert responses[1].chunk.choices[0].finish_reason == "stop"
    mock_node_repository.send_inference_request.assert_awaited_once_with("1", request)
    mock_node_repository.cleanup_request.assert_awaited_once_with("1", "request_id")


async def test_streaming_usage_includes_extra_chunk(connected_node_factory):
    mock_node_repository = MagicMock(NodeRepository)
    mock_tokens_repository = MagicMock(TokensRepository)
    mock_node_repository.select_node = MagicMock(
        return_value=connected_node_factory("1")
    )
    mock_node_repository.send_inference_request = AsyncMock()
    mock_node_repository.receive_for_request = AsyncMock(
        side_effect=[
            InferenceResponse(
                request_id="request_id",
                chunk=MagicMock(choices=[MagicMock(finish_reason=None)], usage=None),
                error=None,
            ),
            InferenceResponse(
                request_id="request_id",
                chunk=MagicMock(choices=[MagicMock(finish_reason="stop")], usage=None),
                error=None,
            ),
            InferenceResponse(
                request_id="request_id",
                chunk=MagicMock(choices=[], usage=None),
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
    async for response in use_case.execute(
        USER_UUID, request, mock_node_repository, mock_tokens_repository, AsyncMock()
    ):
        responses.append(response)

    # 2 content chunks, 1 extra chunk for usage
    assert len(responses) == 3
    assert responses[0].request_id == "request_id"
    assert responses[1].request_id == "request_id"
    assert responses[1].chunk.choices[0].finish_reason == "stop"
    mock_node_repository.send_inference_request.assert_awaited_once_with("1", request)
    mock_node_repository.cleanup_request.assert_awaited_once_with("1", "request_id")
