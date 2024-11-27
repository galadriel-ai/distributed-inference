import base64
from typing import Optional, Union
from openai.types.images_response import ImagesResponse
from openai.types.image import Image
from distributedinference.domain.node.entities import ConnectedNode
from uuid_extensions import uuid7

from distributedinference import api_logger
from distributedinference.analytics.analytics import Analytics
from distributedinference.repository.metrics_queue_repository import (
    MetricsQueueRepository,
)
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.service import error_responses
from distributedinference.service.images.entities import (
    ImageEditRequest,
    ImageGenerationRequest,
    ImageGenerationWebsocketRequest,
)
from distributedinference.utils.google_cloud_storage import GoogleCloudStorage

logger = api_logger.get()


async def execute(
    request: Union[ImageGenerationRequest, ImageEditRequest],
    node_repository: NodeRepository,
    gcs_client: GoogleCloudStorage,
) -> ImagesResponse:
    websocket_request = None
    if isinstance(request, ImageGenerationRequest):
        websocket_request = ImageGenerationWebsocketRequest(
            request_id=str(uuid7()),
            prompt=request.prompt,
            image=None,
            n=request.n,
            size=request.size,
        )
    elif isinstance(request, ImageEditRequest):
        websocket_request = ImageGenerationWebsocketRequest(
            request_id=str(uuid7()),
            prompt=request.prompt,
            image=request.image,
            n=request.n,
            size=request.size,
        )
    else:
        raise ValueError("Invalid request type for image generation")

    logger.info(
        f"Executing image generation service request: {websocket_request.request_id}"
    )

    node = _select_node(node_repository, request.model)
    if not node:
        logger.error(
            f"No available nodes to process the image generation request {websocket_request.request_id}"
        )
        raise error_responses.NoAvailableInferenceNodesError()

    await node_repository.send_image_generation_request(node.uid, websocket_request)

    response = await node_repository.receive_for_image_generation_request(
        node.uid, websocket_request.request_id
    )
    if not response:
        logger.error(
            f"Image generation service request {websocket_request.request_id} failed with error response"
        )
        raise error_responses.InternalServerAPIError()

    logger.info(f"Image generation service request: {response} received")
    # Return base64 encoded images if it is requested
    if request.response_format == "b64_json":
        return ImagesResponse(
            created=len(response.images),
            data=[Image(b64_json=image) for image in response.images],
        )
    else:
        # Upload images to GCS and return URLs
        return ImagesResponse(
            created=len(response.images),
            data=[
                Image(
                    url=await gcs_client.decode_b64_and_upload_to_gcs(
                        websocket_request.request_id, image
                    )
                )
                for image in response.images
            ],
        )


def _select_node(
    node_repository: NodeRepository,
    request_model: str,
) -> Optional[ConnectedNode]:
    node = node_repository.select_node(request_model)
    if not node:
        return None
    return node
