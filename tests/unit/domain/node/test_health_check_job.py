import time
import pytest

from uuid import UUID

from packaging.version import Version
from unittest.mock import AsyncMock, MagicMock, patch

from distributedinference.domain.node.entities import (
    ConnectedNode,
    CheckHealthResponse,
    InferenceError,
    InferenceErrorStatusCodes,
)
from distributedinference.analytics.analytics import (
    Analytics,
    AnalyticsEvent,
    EventName,
)
from distributedinference.domain.node.entities import NodeStatus
from distributedinference.domain.node.entities import InferenceResponse
from distributedinference.domain.node.entities import InferenceStatusCodes
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.domain.node import health_check_job
from distributedinference.service.node.protocol.protocol_handler import ProtocolHandler


@pytest.fixture
def create_mock_node():
    def _create_mock_node(version="0.0.16"):
        return ConnectedNode(
            uid=UUID("6b1f4b1e-0b1b-4b1b-8b1b-1b1f4b1e0b1c"),
            user_id=UUID("6b1f4b1e-0b1b-4b1b-8b1b-1b1f4b1e0b1d"),
            model="model-1",
            vram=16000,
            connected_at=int(time.time()),
            websocket=MagicMock(),
            request_incoming_queues={},
            node_status=NodeStatus.RUNNING_DEGRADED,
            version=Version(version),
        )

    return _create_mock_node


@pytest.fixture
def mock_node_repository():
    repository = AsyncMock(spec=NodeRepository)
    repository.get_node_status = AsyncMock(return_value=NodeStatus.RUNNING)
    return repository


@pytest.fixture
def mock_analytics():
    return MagicMock(spec=Analytics)


@pytest.fixture
def mock_protocol_handler():
    return MagicMock(spec=ProtocolHandler)


@patch("distributedinference.domain.node.health_check_job._send_health_check_inference")
async def test_check_node_health_healthy(
    mock_send_health_check_inference,
    create_mock_node,
    mock_node_repository,
    mock_analytics,
    mock_protocol_handler,
):
    mock_node = create_mock_node()
    healthy_response = CheckHealthResponse(
        node_id=mock_node.uid,
        is_healthy=True,
        error=None,
    )
    mock_send_health_check_inference.return_value = healthy_response

    await health_check_job._check_node_health(
        mock_node, mock_node_repository, mock_analytics, mock_protocol_handler
    )

    mock_node_repository.update_node_status.assert_called_once_with(
        mock_node.uid, NodeStatus.RUNNING
    )
    mock_analytics.track_event.assert_called_once_with(
        mock_node.user_id,
        AnalyticsEvent(
            EventName.NODE_HEALTH, {"node_id": mock_node.uid, "is_healthy": True}
        ),
    )


@patch("distributedinference.domain.node.health_check_job._send_health_check_inference")
async def test_check_node_health_unhealthy(
    mock_send_health_check_inference,
    create_mock_node,
    mock_node_repository,
    mock_analytics,
    mock_protocol_handler,
):
    mock_node = create_mock_node()
    unhealthy_response = CheckHealthResponse(
        node_id=mock_node.uid,
        is_healthy=False,
        error=InferenceError(
            status_code=InferenceErrorStatusCodes.INTERNAL_SERVER_ERROR,
            message="Node did not respond to health check request",
        ),
    )
    mock_send_health_check_inference.return_value = unhealthy_response

    await health_check_job._check_node_health(
        mock_node, mock_node_repository, mock_analytics, mock_protocol_handler
    )

    mock_node_repository.update_node_status.assert_called_once_with(
        mock_node.uid, NodeStatus.RUNNING_DEGRADED
    )
    mock_analytics.track_event.assert_called_once_with(
        mock_node.user_id,
        AnalyticsEvent(
            EventName.NODE_HEALTH, {"node_id": mock_node.uid, "is_healthy": False}
        ),
    )


async def test_check_node_health_exception(
    create_mock_node, mock_node_repository, mock_analytics, mock_protocol_handler
):
    mock_node = create_mock_node()
    mock_node_repository.receive_for_request.side_effect = Exception("Ooops")

    await health_check_job._check_node_health(
        mock_node, mock_node_repository, mock_analytics, mock_protocol_handler
    )

    mock_node_repository.update_node_status.assert_not_called()  # Since exception occurs
    mock_analytics.track_event.assert_called_once_with(
        mock_node.user_id,
        AnalyticsEvent(
            EventName.NODE_HEALTH, {"node_id": mock_node.uid, "is_healthy": False}
        ),
    )


async def test_check_node_health_skips_disabled(
    create_mock_node, mock_node_repository, mock_analytics, mock_protocol_handler
):
    mock_node = create_mock_node()
    mock_node_repository.get_node_status.return_value = NodeStatus.RUNNING_DISABLED
    mock_node_repository.receive_for_request.side_effect = Exception("Ooops")

    await health_check_job._check_node_health(
        mock_node, mock_node_repository, mock_analytics, mock_protocol_handler
    )

    mock_node_repository.send_inference_request.assert_not_called()


async def test_send_health_check_inference_healthy(
    create_mock_node, mock_node_repository
):
    mock_node = create_mock_node()
    mock_node_repository.receive_for_request = AsyncMock(
        side_effect=[
            InferenceResponse(
                node_id=mock_node.uid,
                request_id="request_id",
                chunk=MagicMock(choices=[MagicMock(finish_reason=None)], usage=None),
                error=None,
            ),
            InferenceResponse(
                node_id=mock_node.uid,
                request_id="request_id",
                chunk=MagicMock(choices=[MagicMock(finish_reason="stop")], usage=None),
                error=None,
            ),
            InferenceResponse(
                node_id=mock_node.uid,
                request_id="request_id",
                chunk=None,
                error=None,
                status=InferenceStatusCodes.DONE,
            ),
        ]
    )
    health_check_job.is_node_performant = MagicMock()
    health_check_job.is_node_performant.execute.return_value = True

    response = await health_check_job._send_health_check_inference(
        mock_node, mock_node_repository
    )

    assert response.is_healthy is True
    assert response.error is None

    mock_node_repository.send_inference_request.assert_called_once()
    call_args = mock_node_repository.send_inference_request.call_args
    node_id, inference_request = call_args[0]
    assert node_id == mock_node.uid
    assert inference_request.model == mock_node.model
    assert inference_request.chat_request["model"] == mock_node.model

    mock_node_repository.cleanup_request.assert_called_once()
    call_args = mock_node_repository.cleanup_request.call_args
    node_id, inference_request = call_args[0]
    assert node_id == mock_node.uid


async def test_send_health_check_inference_healthy_old_node(
    create_mock_node, mock_node_repository
):
    healthy_response = AsyncMock(
        chunk=MagicMock(usage=MagicMock(total=10), choices=[]), error=None
    )
    mock_node = create_mock_node(version="0.0.15")
    mock_node_repository.receive_for_request.return_value = healthy_response
    health_check_job.is_node_performant = MagicMock()
    health_check_job.is_node_performant.execute.return_value = True

    response = await health_check_job._send_health_check_inference(
        mock_node, mock_node_repository
    )

    assert response.is_healthy is True
    assert response.error is None

    mock_node_repository.send_inference_request.assert_called_once()
    call_args = mock_node_repository.send_inference_request.call_args
    node_id, inference_request = call_args[0]
    assert node_id == mock_node.uid
    assert inference_request.model == mock_node.model
    assert inference_request.chat_request["model"] == mock_node.model

    mock_node_repository.cleanup_request.assert_called_once()
    call_args = mock_node_repository.cleanup_request.call_args
    node_id, inference_request = call_args[0]
    assert node_id == mock_node.uid


async def test_send_health_check_inference_unhealthy(
    create_mock_node, mock_node_repository
):
    unhealthy_response = None
    mock_node = create_mock_node()
    mock_node_repository.receive_for_request.return_value = unhealthy_response

    response = await health_check_job._send_health_check_inference(
        mock_node, mock_node_repository
    )

    assert response.is_healthy is False
    assert response.error.status_code == InferenceErrorStatusCodes.INTERNAL_SERVER_ERROR
    assert response.error.message == "Node did not respond to health check request"

    mock_node_repository.send_inference_request.assert_called_once()
    call_args = mock_node_repository.send_inference_request.call_args
    node_id, inference_request = call_args[0]
    assert node_id == mock_node.uid
    assert inference_request.model == mock_node.model
    assert inference_request.chat_request["model"] == mock_node.model

    mock_node_repository.cleanup_request.assert_called_once()
    call_args = mock_node_repository.cleanup_request.call_args
    node_id, inference_request = call_args[0]
    assert node_id == mock_node.uid


async def test_send_health_check_inference_error_response(
    create_mock_node, mock_node_repository
):
    error_response = AsyncMock(
        chunk=None,
        error=InferenceError(
            status_code=InferenceErrorStatusCodes.INTERNAL_SERVER_ERROR,
            message="Node encountered an error",
        ),
    )
    mock_node = create_mock_node()
    mock_node_repository.receive_for_request.return_value = error_response

    response = await health_check_job._send_health_check_inference(
        mock_node, mock_node_repository
    )

    assert response.is_healthy is False
    assert response.error.status_code == InferenceErrorStatusCodes.INTERNAL_SERVER_ERROR
    assert response.error.message == "Node encountered an error"
    mock_node_repository.send_inference_request.assert_called_once()
    call_args = mock_node_repository.send_inference_request.call_args
    node_id, inference_request = call_args[0]
    assert node_id == mock_node.uid
    assert inference_request.model == mock_node.model
    assert inference_request.chat_request["model"] == mock_node.model

    mock_node_repository.cleanup_request.assert_called_once()
    call_args = mock_node_repository.cleanup_request.call_args
    node_id, inference_request = call_args[0]
    assert node_id == mock_node.uid
