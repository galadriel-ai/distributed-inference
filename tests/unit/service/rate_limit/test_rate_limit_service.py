import pytest
from unittest.mock import patch
from unittest.mock import AsyncMock
from datetime import datetime, timedelta, timezone
from uuid import UUID

from uuid_extensions import uuid7

from distributedinference.domain.rate_limit.entities import UsageTier
from distributedinference.domain.rate_limit.entities import UserRateLimit
from distributedinference.domain.user.entities import User
from distributedinference.repository.tokens_repository import UsageInformation
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.repository.rate_limit_repository import RateLimitRepository
from distributedinference.service.rate_limit import rate_limit_service as service
from distributedinference.service.rate_limit.entities import RateLimit


async def test_success():
    service.rate_limit_use_case = AsyncMock()
    service.rate_limit_use_case.execute.return_value = UserRateLimit(
        rate_limited=False,
        retry_after=None,
        rate_limit_requests=12,
        rate_limit_tokens=12,
        rate_limit_remaining_requests=12,
        rate_limit_remaining_tokens=12,
        rate_limit_reset_requests=12,
        rate_limit_reset_tokens=12,
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
    assert response == RateLimit(
        rate_limited=False,
        retry_after=None,
        rate_limit_requests=12,
        rate_limit_tokens=12,
        rate_limit_remaining_requests=12,
        rate_limit_remaining_tokens=12,
        rate_limit_reset_requests=12,
        rate_limit_reset_tokens=12,
    )
