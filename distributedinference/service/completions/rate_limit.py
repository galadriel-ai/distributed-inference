from uuid import UUID
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional

from distributedinference.domain.user.entities import User
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.repository.rate_limit_repository import RateLimitRepository
from distributedinference.service.completions.entities import RateLimit


RESET_REQUESTS = 60
RESET_TOKENS = 60
SECONDS_IN_A_MINUTE = 60
SECONDS_IN_A_DAY = 86400


@dataclass
class RateLimitResult:
    rate_limited: bool
    retry_after: Optional[int]
    remaining: Optional[int]


class UsageTierNotFoundError(Exception):
    pass


async def check_rate_limit(
    user: User,
    tokens_repository: TokensRepository,
    rate_limit_repository: RateLimitRepository,
) -> RateLimit:
    usage_tier = await rate_limit_repository.get_usage_tier(user.usage_tier_id)
    if not usage_tier:
        raise UsageTierNotFoundError("Usage tier not found")

    rate_limited = False
    retry_after = None
    remaining_requests = None
    remaining_tokens = None

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
    retry_after = min(
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

    remaining_requests = _get_min_value(
        [request_min_result.remaining, request_day_result.remaining]
    )
    remaining_tokens = _get_min_value(
        [tokens_min_result.remaining, tokens_day_result.remaining]
    )

    return RateLimit(
        rate_limited=rate_limited,
        retry_after=retry_after,
        rate_limit_requests=usage_tier.max_requests_per_day,
        rate_limit_tokens=usage_tier.max_tokens_per_minute,
        rate_limit_remaining_requests=remaining_requests,
        rate_limit_remaining_tokens=remaining_tokens,
        rate_limit_reset_requests=RESET_REQUESTS,
        rate_limit_reset_tokens=RESET_TOKENS,
    )


async def _check_limit(
    limit_value: Optional[int], usage_function, user_id: UUID, seconds: int
) -> RateLimitResult:
    if not limit_value:
        return RateLimitResult(rate_limited=False, retry_after=None, remaining=None)

    usage = await usage_function(user_id, seconds)
    if usage.count >= limit_value:
        time_to_reset = seconds - _elapsed_seconds(usage.oldest_usage_created_at)
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


def _get_min_value(values: list[Optional[int]]) -> Optional[int]:
    filtered_values = [value for value in values if value is not None]
    return min(filtered_values) if filtered_values else None
