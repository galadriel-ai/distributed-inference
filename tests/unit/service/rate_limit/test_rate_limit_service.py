from datetime import datetime
from unittest.mock import AsyncMock
from uuid import UUID

from uuid_extensions import uuid7

from distributedinference.domain.rate_limit.entities import RateLimit
from distributedinference.domain.rate_limit.entities import UsageTier
from distributedinference.domain.rate_limit.entities import UserRateLimitResponse
from distributedinference.domain.user.entities import User
from distributedinference.service.rate_limit import rate_limit_service as service
from distributedinference.service.rate_limit.entities import RateLimitResponse
from distributedinference.service.rate_limit.entities import SingleRateLimit


def _get_usage_tier():
    return UsageTier(
        id=uuid7(),
        name="usage tier",
        description="usage tier description",
        max_tokens_per_minute=12,
        max_tokens_per_day=12,
        max_requests_per_minute=12,
        max_requests_per_day=12,
        created_at=datetime(2024, 1, 1),
        last_updated_at=datetime(2024, 1, 1),
    )


async def test_success():
    service.rate_limit_use_case = AsyncMock()
    service.rate_limit_use_case.execute.return_value = UserRateLimitResponse(
        usage_tier=_get_usage_tier(),
        rate_limited=False,
        retry_after=None,
        rate_limit_minute=RateLimit(
            max_requests=12,
            max_tokens=12,
            remaining_requests=12,
            remaining_tokens=12,
            reset_requests=12,
            reset_tokens=12,
        ),
        rate_limit_day=RateLimit(
            max_requests=120,
            max_tokens=120,
            remaining_requests=120,
            remaining_tokens=120,
            reset_requests=120,
            reset_tokens=120,
        ),
    )
    response = await service.execute(
        User(
            uid=uuid7(),
            name="mock_name",
            email="mock_email",
            usage_tier_id=UUID("06706644-2409-7efd-8000-3371c5d632d3"),
        ),
        AsyncMock(),
        AsyncMock(),
    )
    assert response == RateLimitResponse(
        rate_limited=False,
        retry_after=None,
        usage_tier_name=_get_usage_tier().name,
        usage_tier_description=_get_usage_tier().description,
        rate_limit_minute=SingleRateLimit(
            max_requests=12,
            max_tokens=12,
            remaining_requests=12,
            remaining_tokens=12,
            reset_requests=12,
            reset_tokens=12,
        ),
        rate_limit_day=SingleRateLimit(
            max_requests=120,
            max_tokens=120,
            remaining_requests=120,
            remaining_tokens=120,
            reset_requests=120,
            reset_tokens=120,
        ),
    )
