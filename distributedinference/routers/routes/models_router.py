from fastapi import APIRouter
from fastapi import Depends

from distributedinference import dependencies
from distributedinference.repository.rate_limit_repository import RateLimitRepository
from distributedinference.service.models import get_models_service
from distributedinference.service.models.entities import ModelsResponse

TAG = "Models"
router = APIRouter(prefix="/models")
router.tags = [TAG]


@router.get(
    "",
    summary="Returns available models.",
    description="",
    response_description="",
    response_model=ModelsResponse,
)
async def models(
    rate_limit_repository: RateLimitRepository = Depends(
        dependencies.get_rate_limit_repository
    ),
):
    return await get_models_service.execute(rate_limit_repository)
