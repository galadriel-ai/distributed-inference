from uuid import UUID

import pytest
from unittest.mock import AsyncMock, MagicMock
from distributedinference.domain.node.entities import (
    InferenceRequest,
    InferenceResponse,
)
from distributedinference.domain.node import run_inference_use_case as use_case
from distributedinference.domain.node.exceptions import NoAvailableNodesError
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.service.completions.entities import Message
from distributedinference.service.completions.entities import ChatCompletionRequest
from distributedinference.service.completions.entities import StreamOptions

USER_UUID = UUID("066d0263-61d3-76a4-8000-6b1403cac403")


async def test_success():
    mock_node_repository = MagicMock(NodeRepository)
    mock_tokens_repository = MagicMock(TokensRepository)
    mock_node_repository.select_node = MagicMock(
        return_value=AsyncMock(uid="mock_node")
    )
    mock_node_repository.send_inference_request = AsyncMock()
    mock_node_repository.receive_for_request = AsyncMock(
        side_effect=[
            InferenceResponse(
                request_id="request_id",
                chunk=MagicMock(),
                error=None,
            ),
            InferenceResponse(
                request_id="request_id",
                chunk=MagicMock(choices=[MagicMock(finish_reason="stop")]),
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
        USER_UUID, request, mock_node_repository, mock_tokens_repository
    ):
        responses.append(response)

    assert len(responses) == 2
    assert responses[0].request_id == "request_id"
    assert responses[1].request_id == "request_id"
    assert responses[1].chunk.choices[0].finish_reason == "stop"
    mock_node_repository.send_inference_request.assert_awaited_once_with(
        "mock_node", request
    )
    mock_node_repository.cleanup_request.assert_awaited_once_with(
        "mock_node", "request_id"
    )


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
            USER_UUID, request, mock_node_repository, mock_tokens_repository
        ):
            pass


async def test_streaming_no_usage():
    mock_node_repository = MagicMock(NodeRepository)
    mock_tokens_repository = MagicMock(TokensRepository)
    mock_node_repository.select_node = MagicMock(
        return_value=AsyncMock(uid="mock_node")
    )
    mock_node_repository.send_inference_request = AsyncMock()
    mock_node_repository.receive_for_request = AsyncMock(
        side_effect=[
            InferenceResponse(
                request_id="request_id",
                chunk=MagicMock(choices=[MagicMock(finish_reason=None)]),
                error=None,
            ),
            InferenceResponse(
                request_id="request_id",
                chunk=MagicMock(choices=[MagicMock(finish_reason="stop")]),
                error=None,
            ),
            InferenceResponse(
                request_id="request_id",
                chunk=MagicMock(choices=[]),
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
        USER_UUID, request, mock_node_repository, mock_tokens_repository
    ):
        responses.append(response)

    assert len(responses) == 2
    assert responses[0].request_id == "request_id"
    assert responses[1].request_id == "request_id"
    assert responses[1].chunk.choices[0].finish_reason == "stop"
    mock_node_repository.send_inference_request.assert_awaited_once_with(
        "mock_node", request
    )
    mock_node_repository.cleanup_request.assert_awaited_once_with(
        "mock_node", "request_id"
    )


async def test_streaming_usage_includes_extra_chunk():
    mock_node_repository = MagicMock(NodeRepository)
    mock_tokens_repository = MagicMock(TokensRepository)
    mock_node_repository.select_node = MagicMock(
        return_value=AsyncMock(uid="mock_node")
    )
    mock_node_repository.send_inference_request = AsyncMock()
    mock_node_repository.receive_for_request = AsyncMock(
        side_effect=[
            InferenceResponse(
                request_id="request_id",
                chunk=MagicMock(choices=[MagicMock(finish_reason=None)]),
                error=None,
            ),
            InferenceResponse(
                request_id="request_id",
                chunk=MagicMock(choices=[MagicMock(finish_reason="stop")]),
                error=None,
            ),
            InferenceResponse(
                request_id="request_id",
                chunk=MagicMock(choices=[]),
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
        USER_UUID, request, mock_node_repository, mock_tokens_repository
    ):
        responses.append(response)

    # 2 content chunks, 1 extra chunk for usage
    assert len(responses) == 3
    assert responses[0].request_id == "request_id"
    assert responses[1].request_id == "request_id"
    assert responses[1].chunk.choices[0].finish_reason == "stop"
    mock_node_repository.send_inference_request.assert_awaited_once_with(
        "mock_node", request
    )
    mock_node_repository.cleanup_request.assert_awaited_once_with(
        "mock_node", "request_id"
    )
