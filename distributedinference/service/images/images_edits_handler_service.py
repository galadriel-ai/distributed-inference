from openai.types.images_response import ImagesResponse
from uuid_extensions import uuid7

from distributedinference import api_logger
from distributedinference.domain.node.entities import ImageGenerationWebsocketRequest
from distributedinference.repository.connected_node_repository import (
    ConnectedNodeRepository,
)
from distributedinference.service.images import images_generations_service
from distributedinference.service.images.entities import (
    ImageEditRequest,
)
from distributedinference.utils.google_cloud_storage import GoogleCloudStorage

logger = api_logger.get()


async def execute(
    request: ImageEditRequest,
    connected_node_repository: ConnectedNodeRepository,
    gcs_client: GoogleCloudStorage,
) -> ImagesResponse:
    websocket_request = ImageGenerationWebsocketRequest(
        request_id=str(uuid7()),
        prompt=request.prompt,
        image=request.image,
        n=request.n,
        size=request.size,
    )
    return await images_generations_service.execute(
        websocket_request,
        request.model,
        request.response_format,
        connected_node_repository,
        gcs_client,
    )
