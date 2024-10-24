from datetime import datetime
from uuid import UUID

from distributedinference.domain.rate_limit import check_limit_use_case as use_case
from distributedinference.domain.rate_limit.entities import RateLimitResult
from distributedinference.repository.tokens_repository import UsageInformation

USER_ID = UUID("06719054-738a-7105-8000-9fe3ce617cc9")


async def mock_usage_function(user_id: UUID, model: str, seconds: int):
    return UsageInformation(
        count=1337,
        oldest_usage_id=None,
        oldest_usage_created_at=datetime(2024, 2, 1),
    )


async def test_no_limit():
    result = await use_case.execute(
        "model",
        None,
        mock_usage_function,
        USER_ID,
        60,
    )
    assert result == RateLimitResult(
        rate_limited=False,
        retry_after=None,
        remaining=None,
        usage_count=1337,
    )


async def test_under_usage_max():
    result = await use_case.execute(
        "model",
        2000,
        mock_usage_function,
        USER_ID,
        60,
    )
    assert result == RateLimitResult(
        rate_limited=False,
        retry_after=None,
        remaining=2000 - 1337,
        usage_count=1337,
    )


async def test_over_usage_max():
    result = await use_case.execute(
        "model",
        1000,
        mock_usage_function,
        USER_ID,
        60,
    )
    assert result == RateLimitResult(
        rate_limited=True,
        retry_after=0,
        remaining=0,
        usage_count=1337,
    )
