import settings
from distributedinference.domain.rate_limit import check_limit_use_case
from distributedinference.domain.rate_limit import check_daily_limits_use_case
from distributedinference.domain.rate_limit.entities import UserUsage
from distributedinference.domain.rate_limit.entities import UserUsageLimitsResponse
from distributedinference.domain.user.entities import User
from distributedinference.repository.billing_repository import BillingRepository
from distributedinference.repository.rate_limit_repository import RateLimitRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.service import error_responses

SECONDS_IN_A_DAY = 86400


async def execute(
    user: User,
    tokens_repository: TokensRepository,
    rate_limit_repository: RateLimitRepository,
    billing_repository: BillingRepository,
) -> UserUsageLimitsResponse:
    usage_tier_info = await rate_limit_repository.get_usage_tier_info(
        user.usage_tier_id
    )
    if not usage_tier_info:
        usage_tier_info = await rate_limit_repository.get_usage_tier_info(
            settings.DEFAULT_USAGE_TIER_UUID
        )
        if not usage_tier_info:
            raise error_responses.NotFoundAPIError("Usage tier not found")
    limits = await rate_limit_repository.get_usage_tier_limits(user.usage_tier_id)

    usages = []
    for limit in limits:
        day_limits = await check_daily_limits_use_case.execute(
            tokens_repository,
            limit.model,
            limit.max_requests_per_day,
            limit.max_tokens_per_day,
            user.uid,
        )
        usages.append(
            UserUsage(
                model=limit.model,
                max_tokens_per_minute=limit.max_tokens_per_minute,
                max_tokens_per_day=limit.max_tokens_per_day,
                max_requests_per_minute=limit.max_requests_per_minute,
                max_requests_per_day=limit.max_requests_per_day,
                requests_left_day=day_limits.requests_remaining,
                requests_usage_day=day_limits.requests_count,
                tokens_left_day=day_limits.tokens_remaining,
                tokens_usage_day=day_limits.tokens_count,
                price_per_million_tokens=limit.price_per_million_tokens,
            )
        )

    credits = await billing_repository.get_user_credit_balance(user.uid)
    return UserUsageLimitsResponse(
        name=usage_tier_info.name,
        description=usage_tier_info.description,
        credits=credits,
        usages=usages,
    )
