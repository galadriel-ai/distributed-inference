from fastapi import APIRouter
from fastapi import Depends

from openai.types.images_response import ImagesResponse

from distributedinference import api_logger
from distributedinference import dependencies
from distributedinference.analytics.analytics import Analytics
from distributedinference.analytics.analytics import AnalyticsEvent
from distributedinference.analytics.analytics import EventName
from distributedinference.domain.user.entities import User
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.auth import authentication
from distributedinference.service.images import images_generations_service
from distributedinference.service.images.entities import (
    ImageEditRequest,
    ImageGenerationRequest,
)

TAG = "Images"
router = APIRouter(prefix="/images")
router.tags = [TAG]

logger = api_logger.get()


@router.post(
    "/generations",
    summary="Creates an image given a prompt.",
    description="Given a prompt, the model will generate a image.",
    response_description="Returns a list of image objects.",
    response_model=ImagesResponse,
)
# pylint: disable=too-many-arguments, R0801
async def generations(
    request: ImageGenerationRequest,
    user: User = Depends(authentication.validate_api_key_header),
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    analytics: Analytics = Depends(dependencies.get_analytics),
):
    analytics.track_event(user.uid, AnalyticsEvent(EventName.IMAGE_GENERATION, {}))
    return await images_generations_service.execute(
        request,
        node_repository,
    )


@router.post(
    "/edits",
    summary="Creates an edited or extended image given an original image and a prompt.",
    description="Given a prompt and an original image, the model will generate a new image.",
    response_description="Returns a list of image objects.",
    response_model=ImagesResponse,
)
# pylint: disable=too-many-arguments, R0801
async def edits(
    request: ImageEditRequest,
    user: User = Depends(authentication.validate_api_key_header),
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    analytics: Analytics = Depends(dependencies.get_analytics),
):
    analytics.track_event(user.uid, AnalyticsEvent(EventName.IMAGE_EDIT, {}))
    return await images_generations_service.execute(
        request,
        node_repository,
    )
