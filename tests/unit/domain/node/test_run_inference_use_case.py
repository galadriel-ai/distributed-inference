from uuid import UUID

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from openai.types import CompletionUsage
from prometheus_client import CollectorRegistry, Counter, Histogram

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


async def test_inference_metrics():
    registry = CollectorRegistry()
    with patch(
        "distributedinference.domain.node.run_inference_use_case.node_tokens_gauge",
        Counter(
            "node_tokens",
            "Total tokens by model_name and node uid",
            ["model_name", "node_uid"],
            registry=registry,
        ),
    ), patch(
        "distributedinference.domain.node.run_inference_use_case.node_requests_gauge",
        Counter(
            "node_requests",
            "Total requests by model_name and node uid",
            ["model_name", "node_uid"],
            registry=registry,
        ),
    ), patch(
        "distributedinference.domain.node.run_inference_use_case.node_requests_success_gauge",
        Counter(
            "node_requests_success",
            "Total successful requests by model_name and node uid",
            ["model_name", "node_uid"],
            registry=registry,
        ),
    ), patch(
        "distributedinference.domain.node.run_inference_use_case.node_requests_failed_gauge",
        Counter(
            "node_requests_failed",
            "Total failed requests by model_name and node uid",
            ["model_name", "node_uid"],
            registry=registry,
        ),
    ), patch(
        "distributedinference.domain.node.run_inference_use_case.node_time_to_first_token_histogram",
        Histogram(
            "node_time_to_first_token",
            "Time to first token in seconds",
            ["model_name", "node_uid"],
            registry=registry,
        ),
    ) as mock_histogram:
        mock_observe = MagicMock()
        mock_histogram.labels = MagicMock(return_value=MagicMock(observe=mock_observe))

        mock_node_repository = MagicMock(NodeRepository)
        mock_tokens_repository = MagicMock(TokensRepository)
        mock_node_repository.select_node = MagicMock(
            return_value=AsyncMock(uid="mock_node", model="mock_model")
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
                    chunk=MagicMock(
                        choices=[MagicMock(finish_reason="stop")],
                        usage=CompletionUsage(
                            prompt_tokens=4, completion_tokens=6, total_tokens=10
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
        async for response in use_case.execute(
            USER_UUID, request, mock_node_repository, mock_tokens_repository
        ):
            responses.append(response)

        assert len(responses) == 2
        assert responses[0].request_id == "request_id"
        assert responses[1].request_id == "request_id"
        assert responses[1].chunk.choices[0].finish_reason == "stop"
        assert responses[1].chunk.usage.total_tokens == 10
        mock_node_repository.send_inference_request.assert_awaited_once_with(
            "mock_node", request
        )
        mock_node_repository.cleanup_request.assert_awaited_once_with(
            "mock_node", "request_id"
        )

        assert (
            registry.get_sample_value(
                "node_tokens_total",
                {"model_name": "mock_model", "node_uid": "mock_node"},
            )
            == 10
        )
        assert (
            registry.get_sample_value(
                "node_requests_total",
                {"model_name": "mock_model", "node_uid": "mock_node"},
            )
            == 1
        )
        assert (
            registry.get_sample_value(
                "node_requests_success_total",
                {"model_name": "mock_model", "node_uid": "mock_node"},
            )
            == 1
        )
        assert (
            registry.get_sample_value(
                "node_requests_failed_total",
                {"model_name": "mock_model", "node_uid": "mock_node"},
            )
            == None
        )
        mock_histogram.labels("mock_model").observe.assert_called_once()
