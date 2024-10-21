from distributedinference import api_logger
from distributedinference.domain.rate_limit import rate_limit_use_case
from distributedinference.domain.user.entities import User
from distributedinference.repository.rate_limit_repository import RateLimitRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.service.rate_limit.entities import RateLimit
from distributedinference.utils.timer import async_timer

logger = api_logger.get()


@async_timer("rate_limit.check_rate_limit", logger=logger)
async def execute(
    user: User,
    tokens_repository: TokensRepository,
    rate_limit_repository: RateLimitRepository,
) -> RateLimit:
    user_rate_limit = await rate_limit_use_case.execute(
        user, tokens_repository, rate_limit_repository,
    )
    return RateLimit(
        rate_limited=user_rate_limit.rate_limited,
        retry_after=user_rate_limit.retry_after,
        rate_limit_requests=user_rate_limit.rate_limit_requests,
        rate_limit_tokens=user_rate_limit.rate_limit_tokens,
        rate_limit_remaining_requests=user_rate_limit.rate_limit_remaining_requests,
        rate_limit_remaining_tokens=user_rate_limit.rate_limit_remaining_tokens,
        rate_limit_reset_requests=user_rate_limit.rate_limit_reset_requests,
        rate_limit_reset_tokens=user_rate_limit.rate_limit_reset_tokens,
    )
