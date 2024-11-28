import settings
from distributedinference import api_logger
from distributedinference.domain.rate_limit import check_limit_use_case
from distributedinference.domain.rate_limit import check_daily_limits_use_case
from distributedinference.domain.rate_limit.entities import RateLimit
from distributedinference.domain.rate_limit.entities import RateLimitReason
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
    model: str,
    user: User,
    tokens_repository: TokensRepository,
    rate_limit_repository: RateLimitRepository,
) -> UserRateLimitResponse:
    # We probably need some global not model-specific limits as well?
    usage_limits = await rate_limit_repository.get_usage_limits_for_model(
        user.usage_tier_id, model
    )
    if not usage_limits:
        # Use fallback limits
        usage_limits = await rate_limit_repository.get_usage_limits_for_model(
            user.usage_tier_id,
            next(iter(settings.MODEL_NAME_MAPPING.values())),
        )
        if not usage_limits:
            raise UsageTierNotFoundError("Usage tier not found")

    # Check rate limits for requests and tokens per minute and per day
    request_min_result = await check_limit_use_case.execute(
        model,
        usage_limits.max_requests_per_minute,
        tokens_repository.get_requests_usage_by_time_and_consumer,
        user.uid,
        SECONDS_IN_A_MINUTE,
    )
    tokens_min_result = await check_limit_use_case.execute(
        model,
        usage_limits.max_tokens_per_minute,
        tokens_repository.get_tokens_usage_by_time_and_consumer,
        user.uid,
        SECONDS_IN_A_MINUTE,
    )
    day_rate_limit_result = await check_daily_limits_use_case.execute(
        tokens_repository,
        model,
        usage_limits.max_requests_per_day,
        usage_limits.max_tokens_per_day,
        user.uid,
    )

    # Determine overall rate limit status and retry_after time
    if day_rate_limit_result.rate_limit_reason:
        rate_limit_reason = day_rate_limit_result.rate_limit_reason
    elif request_min_result.rate_limited:
        rate_limit_reason = RateLimitReason.RPM
    elif tokens_min_result.rate_limited:
        rate_limit_reason = RateLimitReason.TPM
    else:
        rate_limit_reason = None

    retry_after = max(
        filter(
            None,
            [
                request_min_result.retry_after,
                tokens_min_result.retry_after,
                day_rate_limit_result.retry_after,
            ],
        ),
        default=None,
    )

    return UserRateLimitResponse(
        rate_limit_reason=rate_limit_reason,
        retry_after=retry_after,
        rate_limit_minute=RateLimit(
            max_requests=usage_limits.max_requests_per_minute,
            max_tokens=usage_limits.max_tokens_per_minute,
            remaining_requests=request_min_result.remaining,
            remaining_tokens=tokens_min_result.remaining,
            # TODO figure out how to calculate these
            reset_requests=RESET_REQUESTS,
            reset_tokens=RESET_TOKENS,
        ),
        rate_limit_day=RateLimit(
            max_requests=usage_limits.max_requests_per_day,
            max_tokens=usage_limits.max_tokens_per_day,
            remaining_requests=day_rate_limit_result.requests_remaining,
            remaining_tokens=day_rate_limit_result.tokens_remaining,
            # TODO figure out how to calculate these
            reset_requests=RESET_REQUESTS,
            reset_tokens=RESET_TOKENS,
        ),
    )
