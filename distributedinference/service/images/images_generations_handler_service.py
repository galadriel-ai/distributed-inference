from openai.types.images_response import ImagesResponse

from distributedinference import api_logger
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.images import images_generations_service
from distributedinference.service.images.entities import ImageGenerationRequest
from distributedinference.utils.google_cloud_storage import GoogleCloudStorage


logger = api_logger.get()


async def execute(
    request: ImageGenerationRequest,
    node_repository: NodeRepository,
    gcs_client: GoogleCloudStorage,
) -> ImagesResponse:
    return await images_generations_service.execute(
        request, node_repository, gcs_client
    )
