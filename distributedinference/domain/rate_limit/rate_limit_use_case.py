from datetime import datetime
from datetime import timezone
from typing import Optional
from uuid import UUID

from distributedinference import api_logger
from distributedinference.domain.rate_limit.entities import RateLimit
from distributedinference.domain.rate_limit.entities import RateLimitResult
from distributedinference.domain.rate_limit.entities import UserRateLimitResponse
from distributedinference.domain.user.entities import User
from distributedinference.repository.rate_limit_repository import RateLimitRepository
from distributedinference.repository.tokens_repository import TokensRepository

RESET_REQUESTS = 60
RESET_TOKENS = 60
SECONDS_IN_A_MINUTE = 60
SECONDS_IN_A_DAY = 86400

logger = api_logger.get()


class UsageTierNotFoundError(Exception):
    pass


async def execute(
    user: User,
    tokens_repository: TokensRepository,
    rate_limit_repository: RateLimitRepository,
) -> UserRateLimitResponse:
    usage_tier = await rate_limit_repository.get_usage_tier(user.usage_tier_id)
    if not usage_tier:
        raise UsageTierNotFoundError("Usage tier not found")

    # Check rate limits for requests and tokens per minute and per day
    request_min_result = await _check_limit(
        usage_tier.max_requests_per_minute,
        tokens_repository.get_requests_usage_by_time_and_consumer,
        user.uid,
        SECONDS_IN_A_MINUTE,
    )
    request_day_result = await _check_limit(
        usage_tier.max_requests_per_day,
        tokens_repository.get_requests_usage_by_time_and_consumer,
        user.uid,
        SECONDS_IN_A_DAY,
    )
    tokens_min_result = await _check_limit(
        usage_tier.max_tokens_per_minute,
        tokens_repository.get_tokens_usage_by_time_and_consumer,
        user.uid,
        SECONDS_IN_A_MINUTE,
    )
    tokens_day_result = await _check_limit(
        usage_tier.max_tokens_per_day,
        tokens_repository.get_tokens_usage_by_time_and_consumer,
        user.uid,
        SECONDS_IN_A_DAY,
    )

    # Determine overall rate limit status and retry_after time
    rate_limited = any(
        [
            request_min_result.rate_limited,
            request_day_result.rate_limited,
            tokens_min_result.rate_limited,
            tokens_day_result.rate_limited,
        ]
    )
    retry_after = max(
        filter(
            None,
            [
                request_min_result.retry_after,
                request_day_result.retry_after,
                tokens_min_result.retry_after,
                tokens_day_result.retry_after,
            ],
        ),
        default=None,
    )

    return UserRateLimitResponse(
        usage_tier=usage_tier,
        rate_limited=rate_limited,
        retry_after=retry_after,
        rate_limit_minute=RateLimit(
            max_requests=usage_tier.max_requests_per_minute,
            max_tokens=usage_tier.max_tokens_per_minute,
            remaining_requests=request_min_result.remaining,
            remaining_tokens=tokens_min_result.remaining,
            # TODO figure out how to calculate these
            reset_requests=RESET_REQUESTS,
            reset_tokens=RESET_TOKENS,
        ),
        rate_limit_day=RateLimit(
            max_requests=usage_tier.max_requests_per_day,
            max_tokens=usage_tier.max_tokens_per_day,
            remaining_requests=request_day_result.remaining,
            remaining_tokens=tokens_day_result.remaining,
            # TODO figure out how to calculate these
            reset_requests=RESET_REQUESTS,
            reset_tokens=RESET_TOKENS,
        ),
    )


async def _check_limit(
    limit_value: Optional[int], usage_function, user_id: UUID, seconds: int
) -> RateLimitResult:
    if not limit_value:
        return RateLimitResult(rate_limited=False, retry_after=None, remaining=None)

    usage = await usage_function(user_id, seconds)
    if usage.count >= limit_value:
        time_to_reset = max(
            seconds - _elapsed_seconds(usage.oldest_usage_created_at), 0
        )
        return RateLimitResult(
            rate_limited=True, retry_after=int(time_to_reset), remaining=0
        )

    return RateLimitResult(
        rate_limited=False, retry_after=None, remaining=limit_value - usage.count
    )


def _elapsed_seconds(since: datetime) -> float:
    if since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - since).total_seconds()
