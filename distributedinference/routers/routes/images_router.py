from typing import Optional
from fastapi import APIRouter, UploadFile
from fastapi import Depends
from fastapi import Response

from openai.types.image_generate_params import ImageGenerateParams
from openai.types.image_edit_params import ImageEditParams
from openai.types.images_response import ImagesResponse

from distributedinference import api_logger
from distributedinference import dependencies
from distributedinference.analytics.analytics import Analytics
from distributedinference.analytics.analytics import AnalyticsEvent
from distributedinference.analytics.analytics import EventName
from distributedinference.domain.user.entities import User
from distributedinference.repository.metrics_queue_repository import (
    MetricsQueueRepository,
)
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.repository.rate_limit_repository import RateLimitRepository
from distributedinference.service.auth import authentication
from distributedinference.service.images import images_generations_service
from distributedinference.service.images.entities import ImageEditRequest, ImageGenerationRequest

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
    response: Response,
    user: User = Depends(authentication.validate_api_key_header),
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    tokens_repository: TokensRepository = Depends(dependencies.get_tokens_repository),
    rate_limit_repository: RateLimitRepository = Depends(dependencies.get_rate_limit_repository),
    metrics_queue_repository: MetricsQueueRepository = Depends(
        dependencies.get_metrics_queue_repository
    ),
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
    response: Response,
    user: User = Depends(authentication.validate_api_key_header),
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    tokens_repository: TokensRepository = Depends(dependencies.get_tokens_repository),
    rate_limit_repository: RateLimitRepository = Depends(dependencies.get_rate_limit_repository),
    metrics_queue_repository: MetricsQueueRepository = Depends(
        dependencies.get_metrics_queue_repository
    ),
    analytics: Analytics = Depends(dependencies.get_analytics),
):
    analytics.track_event(user.uid, AnalyticsEvent(EventName.IMAGE_EDIT, {}))
    return await images_generations_service.execute(
        request,
        node_repository,
    )
