import base64
from typing import Literal, Optional
from fastapi import APIRouter, File, Form, UploadFile
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
from distributedinference.utils.google_cloud_storage import GoogleCloudStorage

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
async def generations(
    request: ImageGenerationRequest,
    user: User = Depends(authentication.validate_api_key_header),
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    analytics: Analytics = Depends(dependencies.get_analytics),
    gcs_client: GoogleCloudStorage = Depends(
        dependencies.get_google_cloud_storage_client
    ),
):
    analytics.track_event(user.uid, AnalyticsEvent(EventName.IMAGE_GENERATION, {}))
    return await images_generations_service.execute(
        request, node_repository, gcs_client
    )


@router.post(
    "/edits",
    summary="Creates an edited or extended image given an original image and a prompt.",
    description="Given a prompt and an original image, the model will generate a new image.",
    response_description="Returns a list of image objects.",
    response_model=ImagesResponse,
)
# pylint: disable=too-many-arguments
async def edits(
    image: UploadFile = File(description="The image to be edited."),
    prompt: str = Form(description="A text description of the desired image(s)."),
    model: str = Form(description="The model to use for image editing."),
    n: int = Form(
        description="The number of images to generate. Must be between 1 and 10.",
        ge=1,
        le=10,
        default=1,
    ),
    response_format: Literal["url", "b64_json"] = Form(
        description="The format in which the generated images are returned.",
        default="url",
    ),
    size: Literal["256x256", "512x512", "1024x1024"] = Form(
        description="The size of the generated images.",
        default="1024x1024",
    ),
    user: Optional[str] = Form(
        description="A unique identifier representing your end-user", default=None
    ),
    api_user: User = Depends(authentication.validate_api_key_header),
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    analytics: Analytics = Depends(dependencies.get_analytics),
    gcs_client: GoogleCloudStorage = Depends(
        dependencies.get_google_cloud_storage_client
    ),
):
    analytics.track_event(api_user.uid, AnalyticsEvent(EventName.IMAGE_EDIT, {}))
    image_bytes = await image.read()
    request = ImageEditRequest(
        image=base64.b64encode(image_bytes).decode("utf-8"),
        prompt=prompt,
        model=model,
        mask=None,
        n=n,
        response_format=response_format,
        size=size,
        user=user,
    )
    return await images_generations_service.execute(
        request,
        node_repository,
        gcs_client,
    )
