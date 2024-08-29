import pytest
from unittest.mock import AsyncMock, MagicMock
from distributedinference.domain.node.entities import (
    InferenceRequest,
    InferenceResponse,
)
from distributedinference.domain.node import run_inference_use_case as use_case
from distributedinference.domain.node.exceptions import NoAvailableNodesError
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.completions.entities import Message
from distributedinference.service.completions.entities import ChatCompletionRequest


async def test_success():
    mock_node_repository = MagicMock(NodeRepository)
    mock_node_repository.select_node = MagicMock(return_value="mock_node")
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

    request = InferenceRequest(
        id="request_id",
        model="model-1",
        chat_request=ChatCompletionRequest(
            model="llama3", messages=[Message(role="user", content="asd")]
        ),
    )

    responses = []
    async for response in use_case.execute(request, mock_node_repository):
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
    mock_node_repository.select_node = MagicMock(return_value=None)

    request = InferenceRequest(
        id="request_id",
        model="model-1",
        chat_request=ChatCompletionRequest(
            model="llama3", messages=[Message(role="user", content="asd")]
        ),
    )

    with pytest.raises(NoAvailableNodesError):
        async for response in use_case.execute(request, mock_node_repository):
            pass
