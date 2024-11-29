from openai.types.images_response import ImagesResponse
from distributedinference.domain.node import run_images_generation_use_case

from distributedinference import api_logger
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.images.entities import ImageGenerationWebsocketRequest

from distributedinference.utils.google_cloud_storage import GoogleCloudStorage

logger = api_logger.get()


async def execute(
    websocket_request: ImageGenerationWebsocketRequest,
    model: str,
    response_format: str,
    node_repository: NodeRepository,
    gcs_client: GoogleCloudStorage,
) -> ImagesResponse:
    logger.info(
        f"Executing image generation service request: {websocket_request.request_id}"
    )

    return await run_images_generation_use_case.execute(
        websocket_request, model, response_format, node_repository, gcs_client
    )
