from typing import Optional

from openai.types.images_response import ImagesResponse
from openai.types.image import Image

from distributedinference.domain.node.entities import (
    ConnectedNode,
    ImageGenerationWebsocketRequest,
)
from distributedinference.service import error_responses
from distributedinference.utils.google_cloud_storage import GoogleCloudStorage
from distributedinference import api_logger
from distributedinference.repository.node_repository import NodeRepository

logger = api_logger.get()


async def execute(
    websocket_request: ImageGenerationWebsocketRequest,
    model: str,
    response_format: str,
    node_repository: NodeRepository,
    gcs_client: GoogleCloudStorage,
) -> ImagesResponse:
    node = _select_node(node_repository, model)
    if not node:
        logger.error(
            f"No available nodes to process the image generation request {websocket_request.request_id}"
        )
        raise error_responses.NoAvailableInferenceNodesError()

    await node_repository.send_image_generation_request(node.uid, websocket_request)

    response = await node_repository.receive_for_image_generation_request(
        node.uid, websocket_request.request_id
    )
    if not response or response.error is not None:
        logger.error(
            f"Image generation service request {websocket_request.request_id} failed with error response: {response.error if response else 'no response'}"
        )
        raise error_responses.InternalServerAPIError()

    logger.info(f"Image generation service request: {response} received")
    # Return base64 encoded images if it is requested
    if response_format == "b64_json":
        return ImagesResponse(
            created=len(response.images),
            data=[Image(b64_json=image) for image in response.images],
        )
    # Upload images to GCS and return URLs
    return ImagesResponse(
        created=len(response.images),
        data=[
            Image(
                url=await gcs_client.decode_b64_and_upload_to_gcs(
                    websocket_request.request_id, idx, image
                )
            )
            for idx, image in enumerate(response.images)
        ],
    )


def _select_node(
    node_repository: NodeRepository,
    request_model: str,
) -> Optional[ConnectedNode]:
    return node_repository.select_node(request_model)
