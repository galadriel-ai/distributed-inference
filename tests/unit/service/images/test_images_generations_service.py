import time
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from uuid import UUID
from uuid import uuid1

import pytest
from openai.types.images_response import ImagesResponse
from packaging.version import Version

from distributedinference.domain.node import run_images_generation_use_case
from distributedinference.domain.node.entities import BackendHost, ConnectedNode
from distributedinference.domain.node.entities import ImageGenerationWebsocketResponse
from distributedinference.domain.node.entities import NodeStatus
from distributedinference.repository.connected_node_repository import (
    ConnectedNodeRepository,
)
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service import error_responses
from distributedinference.service.images import (
    images_edits_handler_service as edit_handler_service,
)
from distributedinference.service.images import (
    images_generations_handler_service as generation_handler_service,
)
from distributedinference.service.images.entities import ImageEditRequest
from distributedinference.service.images.entities import ImageGenerationRequest
from distributedinference.utils.google_cloud_storage import GoogleCloudStorage

USER_UUID = UUID("066d0263-61d3-76a4-8000-6b1403cac403")
MOCK_UUID = UUID("a2e3db51-7a7f-473c-8cd5-390e7ed1e1c7")
REQUEST_ID = str(uuid1())


def setup():
    generation_handler_service.uuid7 = MagicMock()
    generation_handler_service.uuid7.return_value = MOCK_UUID
    run_images_generation_use_case._select_node = MagicMock()


@pytest.fixture
def node_repository():
    return AsyncMock(spec=NodeRepository)


@pytest.fixture
def connected_node_repository():
    return AsyncMock(spec=ConnectedNodeRepository)


@pytest.fixture
def image_generation_request():
    return ImageGenerationRequest(
        prompt="A beautiful sunset over the ocean.",
        model="image-generator-v1.0",
        n=1,
        quality="standard",
        response_format="url",
    )


@pytest.fixture
def image_edit_request():
    return ImageEditRequest(
        prompt="A beautiful sunset over the ocean.",
        model="image-generator-v1.0",
        image="base64encodedimage",
        n=1,
        response_format="url",
    )


@pytest.fixture
def node_repository():
    return AsyncMock(NodeRepository)


@pytest.fixture
def gsc_client():
    return AsyncMock(GoogleCloudStorage)


def create_mock_node():
    return ConnectedNode(
        uid=UUID("6b1f4b1e-0b1b-4b1b-8b1b-1b1f4b1e0b1c"),
        user_id=UUID("6b1f4b1e-0b1b-4b1b-8b1b-1b1f4b1e0b1d"),
        model="model-1",
        vram=16000,
        connected_at=int(time.time()),
        connected_host=BackendHost.from_value("distributed-inference-us"),
        websocket=MagicMock(),
        request_incoming_queues={},
        node_status=NodeStatus.RUNNING_DEGRADED,
        version=Version("1.0.0"),
    )


@pytest.mark.asyncio
async def test_execute_image_generation_request(
    connected_node_repository,
    image_generation_request,
    gsc_client,
):
    mock_node = create_mock_node()
    run_images_generation_use_case._select_node = MagicMock(return_value=mock_node)

    expected_b64_image = "base64encodedimage"
    mock_image_websocket_response = ImageGenerationWebsocketResponse(
        node_id=mock_node.uid,
        request_id=REQUEST_ID,
        images=[expected_b64_image],
        error=None,
    )

    connected_node_repository.receive_for_image_generation_request = AsyncMock(
        return_value=mock_image_websocket_response
    )

    gsc_client.decode_b64_and_upload_to_gcs = AsyncMock(
        return_value="https://example.com/image.png"
    )

    response = await generation_handler_service.execute(
        image_generation_request,
        connected_node_repository,
        gsc_client,
    )

    assert isinstance(response, ImagesResponse)
    assert len(response.data) == 1
    assert response.data[0].url == "https://example.com/image.png"


@pytest.mark.asyncio
async def test_execute_image_edit_request(
    connected_node_repository,
    image_edit_request,
    gsc_client,
):
    mock_node = create_mock_node()
    run_images_generation_use_case._select_node = MagicMock(return_value=mock_node)

    expected_b64_image = "base64encodedimage"
    mock_image_websocket_response = ImageGenerationWebsocketResponse(
        node_id=mock_node.uid,
        request_id=REQUEST_ID,
        images=[expected_b64_image],
        error=None,
    )

    connected_node_repository.receive_for_image_generation_request = AsyncMock(
        return_value=mock_image_websocket_response
    )
    gsc_client.decode_b64_and_upload_to_gcs = AsyncMock(
        return_value="https://example.com/image.png"
    )
    response = await edit_handler_service.execute(
        image_edit_request,
        connected_node_repository,
        gsc_client,
    )

    assert isinstance(response, ImagesResponse)
    assert len(response.data) == 1
    assert response.data[0].url == "https://example.com/image.png"


@pytest.mark.asyncio
async def test_execute_no_available_nodes(
    connected_node_repository,
    image_generation_request,
    gsc_client,
):
    run_images_generation_use_case._select_node = MagicMock(return_value=None)

    with pytest.raises(error_responses.NoAvailableInferenceNodesError):
        await generation_handler_service.execute(
            image_generation_request,
            connected_node_repository,
            gsc_client,
        )


@pytest.mark.asyncio
async def test_execute_internal_server_error(
    connected_node_repository,
    image_generation_request,
    gsc_client,
):
    run_images_generation_use_case._select_node = MagicMock(
        return_value=create_mock_node()
    )
    connected_node_repository.receive_for_image_generation_request.return_value = None

    gsc_client.decode_b64_and_upload_to_gcs = AsyncMock(
        side_effect=Exception("Failed to upload image to GCS")
    )

    with pytest.raises(error_responses.InternalServerAPIError):
        await generation_handler_service.execute(
            image_generation_request,
            connected_node_repository,
            gsc_client,
        )
