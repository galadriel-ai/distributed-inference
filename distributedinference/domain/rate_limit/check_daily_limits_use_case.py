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
    request_limit_value: Optional[int],
    token_limit_value: Optional[int],
    user_id: UUID,
) -> DailyRateLimitResult:
    usage = await repository.get_daily_usage(user_id, model)
    if not (request_limit_value or token_limit_value):
        return DailyRateLimitResult(
            rate_limit_reason=None,
            retry_after=None,
            requests_remaining=None,
            tokens_remaining=None,
            requests_count=usage.total_requests_count,
            tokens_count=usage.total_tokens_count,
        )
    if usage.total_requests_count >= request_limit_value:
        return DailyRateLimitResult(
            rate_limit_reason=RateLimitReason.RPD,
            retry_after=_seconds_until_utc_midnight(),
            requests_remaining=0,
            tokens_remaining=token_limit_value - usage.total_tokens_count,
            requests_count=usage.total_requests_count,
            tokens_count=usage.total_tokens_count,
        )
    elif usage.total_tokens_count >= token_limit_value:
        return DailyRateLimitResult(
            rate_limit_reason=RateLimitReason.TPD,
            retry_after=_seconds_until_utc_midnight(),
            requests_remaining=0,
            tokens_remaining=token_limit_value - usage.total_tokens_count,
            requests_count=usage.total_requests_count,
            tokens_count=usage.total_tokens_count,
        )
    return DailyRateLimitResult(
        rate_limit_reason=None,
        retry_after=None,
        requests_remaining=request_limit_value - usage.total_requests_count,
        tokens_remaining=token_limit_value - usage.total_tokens_count,
        requests_count=usage.total_requests_count,
        tokens_count=usage.total_tokens_count,
    )


def _seconds_until_utc_midnight() -> int:
    now = datetime.now(timezone.utc)
    midnight = datetime(
        year=now.year, month=now.month, day=now.day + 1, tzinfo=timezone.utc
    )
    return int((midnight - now).total_seconds())
