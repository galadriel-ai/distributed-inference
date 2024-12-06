from typing import List

import settings
from distributedinference.domain.models.entities import Model
from distributedinference.domain.models.entities import ModelPricing
from distributedinference.repository.rate_limit_repository import RateLimitRepository


async def execute(rate_limit_repository: RateLimitRepository) -> List[Model]:
    models = []
    for tier_id in [settings.DEFAULT_USAGE_TIER_UUID, settings.PAID_USAGE_TIER_UUID]:
        limits = await rate_limit_repository.get_usage_tier_limits(tier_id)
        for limit in limits:
            models.append(
                Model(
                    id=limit.model,
                    name=limit.model,
                    context_length=settings.MODEL_MAX_TOKENS_MAPPING[limit.model],
                    max_completion_tokens=settings.MODEL_MAX_COMPLETION_TOKENS_MAPPING[
                        limit.model
                    ],
                    pricing=ModelPricing(
                        prompt=(
                            str(limit.price_per_million_tokens)
                            if limit.price_per_million_tokens
                            else "0"
                        ),
                        completion=(
                            str(limit.price_per_million_tokens)
                            if limit.price_per_million_tokens
                            else "0"
                        ),
                        image="0",
                        request="0",
                    ),
                )
            )
    return models
