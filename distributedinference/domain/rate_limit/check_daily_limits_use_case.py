from datetime import datetime
from datetime import timezone
from typing import Optional
from uuid import UUID

from distributedinference.domain.rate_limit.entities import RateLimitReason
from distributedinference.domain.rate_limit.entities import DailyRateLimitResult
from distributedinference.repository.tokens_repository import TokensRepository


async def execute(
    repository: TokensRepository,
    model: str,
    max_requests_per_day: Optional[int],
    max_tokens_per_day: Optional[int],
    user_id: UUID,
) -> DailyRateLimitResult:
    usage = await repository.get_daily_usage(user_id, model)
    if not (max_requests_per_day or max_tokens_per_day):
        return DailyRateLimitResult(
            rate_limit_reason=None,
            retry_after=None,
            requests_remaining=None,
            tokens_remaining=None,
            requests_count=usage.total_requests_count,
            tokens_count=usage.total_tokens_count,
        )
    if usage.total_requests_count >= max_requests_per_day:
        return DailyRateLimitResult(
            rate_limit_reason=RateLimitReason.RPD,
            retry_after=_seconds_until_utc_midnight(),
            requests_remaining=0,
            tokens_remaining=max_tokens_per_day - usage.total_tokens_count,
            requests_count=usage.total_requests_count,
            tokens_count=usage.total_tokens_count,
        )
    elif usage.total_tokens_count >= max_tokens_per_day:
        return DailyRateLimitResult(
            rate_limit_reason=RateLimitReason.TPD,
            retry_after=_seconds_until_utc_midnight(),
            requests_remaining=max_requests_per_day - usage.total_requests_count,
            tokens_remaining=0,
            requests_count=usage.total_requests_count,
            tokens_count=usage.total_tokens_count,
        )
    return DailyRateLimitResult(
        rate_limit_reason=None,
        retry_after=None,
        requests_remaining=max_requests_per_day - usage.total_requests_count,
        tokens_remaining=max_tokens_per_day - usage.total_tokens_count,
        requests_count=usage.total_requests_count,
        tokens_count=usage.total_tokens_count,
    )


def _seconds_until_utc_midnight() -> int:
    now = datetime.now(timezone.utc)
    midnight = datetime(
        year=now.year, month=now.month, day=now.day + 1, tzinfo=timezone.utc
    )
    return int((midnight - now).total_seconds())
