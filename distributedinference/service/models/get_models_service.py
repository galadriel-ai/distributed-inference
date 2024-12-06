from typing import List
from distributedinference.domain.models.entities import Model
from distributedinference.domain.models.entities import ModelPricing
from distributedinference.domain.models import get_available_models
from distributedinference.service.models.entities import ModelResponse
from distributedinference.service.models.entities import ModelPricingResponse
from distributedinference.service.models.entities import ModelsResponse
from distributedinference.repository.rate_limit_repository import RateLimitRepository


async def execute(rate_limit_repository: RateLimitRepository) -> ModelsResponse:
    models = await get_available_models.execute(rate_limit_repository)
    return ModelsResponse(data=_convert_models(models))


def _convert_models(models: List[Model]) -> List[ModelResponse]:
    return [
        ModelResponse(
            id=model.id,
            name=model.name,
            context_length=model.context_length,
            max_completion_tokens=model.max_completion_tokens,
            pricing=_convert_pricing(model.pricing),
        )
        for model in models
    ]


def _convert_pricing(pricing: ModelPricing) -> ModelPricingResponse:
    return ModelPricingResponse(
        prompt=pricing.prompt,
        completion=pricing.completion,
        image=pricing.image,
        request=pricing.request,
    )
