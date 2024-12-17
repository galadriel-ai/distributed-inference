import settings
from distributedinference.api_logger import api_logger
from distributedinference.domain.rate_limit import get_user_limits_use_case
from distributedinference.domain.rate_limit.entities import UserUsage
from distributedinference.domain.user.entities import User
from distributedinference.repository.billing_repository import BillingRepository
from distributedinference.repository.rate_limit_repository import RateLimitRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.service.rate_limit.entities import ModelUsage
from distributedinference.service.rate_limit.entities import RateLimitResponse
from distributedinference.utils.timer import async_timer

logger = api_logger.get()


@async_timer("rate_limit.check_rate_limit", logger=logger)
async def execute(
    user: User,
    tokens_repository: TokensRepository,
    rate_limit_repository: RateLimitRepository,
    billing_repository: BillingRepository,
) -> RateLimitResponse:
    limits = await get_user_limits_use_case.execute(
        user,
        tokens_repository,
        rate_limit_repository,
        billing_repository,
    )
    return RateLimitResponse(
        usage_tier_name=limits.name,
        usage_tier_description=limits.description or "",
        credits_balance=f"{limits.credits}" if limits.credits is not None else None,
        usages=[_get_formatted_single_limit(l) for l in limits.usages],
    )


def _get_formatted_single_limit(usage: UserUsage) -> ModelUsage:
    return ModelUsage(
        model=_map_model_name(usage.model),
        full_model=usage.model,
        price_per_million_tokens=(
            f"{usage.price_per_million_tokens}"
            if usage.price_per_million_tokens
            else None
        ),
        max_requests_per_day=usage.max_requests_per_day,
        max_requests_per_minute=usage.max_requests_per_minute,
        max_tokens_per_day=usage.max_tokens_per_day,
        max_tokens_per_minute=usage.max_tokens_per_minute,
        requests_left_day=usage.requests_left_day,
        requests_used_day=usage.requests_usage_day,
        tokens_left_day=usage.tokens_left_day,
        tokens_used_day=usage.tokens_usage_day,
    )


def _map_model_name(full_model: str) -> str:
    for k, v in settings.MODEL_NAME_MAPPING.items():
        if v == full_model:
            return k
    return full_model
