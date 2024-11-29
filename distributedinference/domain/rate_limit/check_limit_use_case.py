from datetime import datetime
from datetime import timezone
from typing import Awaitable
from typing import Callable
from typing import Optional
from uuid import UUID

from distributedinference.domain.rate_limit.entities import RateLimitResult
from distributedinference.repository.tokens_repository import UsageInformation

SECONDS = 60


async def execute(
    model: str,
    limit_value: Optional[int],
    usage_function: Callable[[UUID, str, int], Awaitable[UsageInformation]],
    user_id: UUID,
) -> RateLimitResult:
    usage = await usage_function(user_id, model, SECONDS)
    if not limit_value:
        return RateLimitResult(
            rate_limited=False,
            retry_after=None,
            remaining=None,
            usage_count=usage.count,
        )
    if usage.count >= limit_value:
        time_to_reset = max(
            SECONDS - _elapsed_seconds(usage.oldest_usage_created_at), 0
        )
        return RateLimitResult(
            rate_limited=True,
            retry_after=int(time_to_reset),
            remaining=0,
            usage_count=usage.count,
        )

    return RateLimitResult(
        rate_limited=False,
        retry_after=None,
        remaining=limit_value - usage.count,
        usage_count=usage.count,
    )


def _elapsed_seconds(since: datetime) -> float:
    if since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - since).total_seconds()
