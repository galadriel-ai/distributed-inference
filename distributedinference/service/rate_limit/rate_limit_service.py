from distributedinference import api_logger
from distributedinference.domain.rate_limit import rate_limit_use_case
from distributedinference.domain.rate_limit.entities import RateLimit
from distributedinference.domain.user.entities import User
from distributedinference.repository.rate_limit_repository import RateLimitRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.service.rate_limit.entities import RateLimitResponse
from distributedinference.service.rate_limit.entities import SingleRateLimit
from distributedinference.utils.timer import async_timer

logger = api_logger.get()


@async_timer("rate_limit.check_rate_limit", logger=logger)
async def execute(
    user: User,
    tokens_repository: TokensRepository,
    rate_limit_repository: RateLimitRepository,
) -> RateLimitResponse:
    user_rate_limit = await rate_limit_use_case.execute(
        user,
        tokens_repository,
        rate_limit_repository,
    )
    return RateLimitResponse(
        usage_tier_name=user_rate_limit.usage_tier.name,
        usage_tier_description=user_rate_limit.usage_tier.description,
        rate_limited=user_rate_limit.rate_limited,
        retry_after=user_rate_limit.retry_after,
        rate_limit_minute=_get_formatted_single_limit(
            user_rate_limit.rate_limit_minute
        ),
        rate_limit_day=_get_formatted_single_limit(user_rate_limit.rate_limit_day),
    )


def _get_formatted_single_limit(rate_limit: RateLimit) -> SingleRateLimit:
    return SingleRateLimit(
        max_requests=rate_limit.max_requests,
        max_tokens=rate_limit.max_tokens,
        remaining_requests=rate_limit.remaining_requests,
        remaining_tokens=rate_limit.remaining_tokens,
        reset_requests=rate_limit.reset_requests,
        reset_tokens=rate_limit.reset_tokens,
    )
