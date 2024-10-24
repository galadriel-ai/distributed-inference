from datetime import datetime
from datetime import timedelta
from datetime import timezone
from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import UUID

import pytest
from uuid_extensions import uuid7

from distributedinference.domain.rate_limit import rate_limit_use_case as use_case
from distributedinference.domain.rate_limit.entities import RateLimitResult
from distributedinference.domain.rate_limit.entities import UsageLimits
from distributedinference.domain.rate_limit.entities import UsageTier
from distributedinference.domain.user.entities import User
from distributedinference.repository.rate_limit_repository import RateLimitRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.repository.tokens_repository import UsageInformation


@pytest.fixture
def mock_tokens_repository():
    repository = AsyncMock(TokensRepository)
    repository.get_requests_usage_by_time_and_consumer = AsyncMock()
    repository.get_tokens_usage_by_time_and_consumer = AsyncMock()
    return repository


@pytest.fixture
def mock_rate_limit_repository():
    repository = AsyncMock(RateLimitRepository)
    repository.get_usage_tier = AsyncMock()
    return repository


@pytest.fixture
def user():
    return User(
        uid=uuid7(),
        name="mock_name",
        email="mock_email",
        usage_tier_id=UUID("06706644-2409-7efd-8000-3371c5d632d3"),
    )


@pytest.fixture
def usage_limits():
    return UsageLimits(
        model="model",
        max_requests_per_minute=3,
        max_requests_per_day=100,
        max_tokens_per_minute=1000,
        max_tokens_per_day=10000,
    )


@pytest.fixture
def usage_limits():
    return UsageLimits(
        model="model",
        max_requests_per_minute=3,
        max_requests_per_day=100,
        max_tokens_per_minute=1000,
        max_tokens_per_day=10000,
    )


async def test_rate_limit_not_exceeded(
    mock_tokens_repository, mock_rate_limit_repository, user, usage_limits
):
    mock_rate_limit_repository.get_usage_limits_for_model.return_value = usage_limits
    mock_tokens_repository.get_requests_usage_by_time_and_consumer.return_value = (
        UsageInformation(count=0, oldest_usage_id=None, oldest_usage_created_at=None)
    )
    mock_tokens_repository.get_tokens_usage_by_time_and_consumer.return_value = (
        UsageInformation(count=0, oldest_usage_id=None, oldest_usage_created_at=None)
    )

    use_case.check_limit_use_case = AsyncMock()
    use_case.check_limit_use_case.execute.return_value = RateLimitResult(
        rate_limited=False,
        retry_after=None,
        remaining=123,
        usage_count=67,
    )

    result = await use_case.execute(
        "model", user, mock_tokens_repository, mock_rate_limit_repository
    )

    assert result.rate_limited is False
    assert result.retry_after is None
    assert result.rate_limit_day.remaining_requests == 123
    assert result.rate_limit_day.remaining_tokens == 123
    assert result.rate_limit_minute.remaining_requests == 123
    assert result.rate_limit_minute.remaining_tokens == 123


async def test_rate_limit_exceeded_by_requests_per_minute(
    mock_tokens_repository, mock_rate_limit_repository, user, usage_limits
):
    mock_rate_limit_repository.get_usage_limits_for_model.return_value = usage_limits

    use_case.check_limit_use_case = AsyncMock()
    use_case.check_limit_use_case.execute.side_effect = RateLimitResult(
        rate_limited=False,
        retry_after=None,
        remaining=123,
        usage_count=67,
    )

    class UsageMock:

        count = 0

        async def usage_function(self, *args, **kwargs):
            if self.count != 0:
                result = RateLimitResult(
                    rate_limited=False,
                    retry_after=None,
                    remaining=123,
                    usage_count=67,
                )
            else:
                result = RateLimitResult(
                    rate_limited=True,
                    retry_after=30,
                    remaining=0,
                    usage_count=200,
                )
            self.count += 1
            return result

    usage_mock = UsageMock()

    use_case.check_limit_use_case = AsyncMock()
    use_case.check_limit_use_case.execute.side_effect = usage_mock.usage_function

    result = await use_case.execute(
        "model", user, mock_tokens_repository, mock_rate_limit_repository
    )

    assert result.rate_limited is True
    assert result.retry_after == 30  # Retry after 30 seconds for minute-level limit
    assert result.rate_limit_minute.remaining_requests == 0
    assert result.rate_limit_day.remaining_requests == 123


async def test_rate_limit_exceeded_by_requests_per_day(
    mock_tokens_repository, mock_rate_limit_repository, user, usage_limits
):
    mock_rate_limit_repository.get_usage_tier.return_value = usage_limits

    class UsageMock:

        count = 0

        async def usage_function(self, *args, **kwargs):
            if self.count != 1:
                result = RateLimitResult(
                    rate_limited=False,
                    retry_after=None,
                    remaining=123,
                    usage_count=67,
                )
            else:
                result = RateLimitResult(
                    rate_limited=True,
                    retry_after=68400,
                    remaining=0,
                    usage_count=200,
                )
            self.count += 1
            return result

    usage_mock = UsageMock()

    use_case.check_limit_use_case = AsyncMock()
    use_case.check_limit_use_case.execute.side_effect = usage_mock.usage_function

    result = await use_case.execute(
        "model", user, mock_tokens_repository, mock_rate_limit_repository
    )

    assert result.rate_limited is True
    assert result.retry_after == 68400  # Retry after 19h for day-level limit
    assert result.rate_limit_day.remaining_requests == 0  # No more requests available
    assert result.rate_limit_minute.remaining_requests == 123


async def test_rate_limit_exceeded_by_tokens_per_minute(
    mock_tokens_repository, mock_rate_limit_repository, user, usage_limits
):
    mock_rate_limit_repository.get_usage_tier.return_value = usage_limits

    class UsageMock:

        count = 0

        async def usage_function(self, *args, **kwargs):
            if self.count != 2:
                result = RateLimitResult(
                    rate_limited=False,
                    retry_after=None,
                    remaining=123,
                    usage_count=67,
                )
            else:
                result = RateLimitResult(
                    rate_limited=True,
                    retry_after=30,
                    remaining=0,
                    usage_count=200,
                )
            self.count += 1
            return result

    usage_mock = UsageMock()

    use_case.check_limit_use_case = AsyncMock()
    use_case.check_limit_use_case.execute.side_effect = usage_mock.usage_function
    result = await use_case.execute(
        "model", user, mock_tokens_repository, mock_rate_limit_repository
    )

    assert result.rate_limited is True
    assert (
        result.retry_after == 30
    )  # Retry after remaining 30 seconds for the minute-level token limit
    assert result.rate_limit_minute.remaining_tokens == 0
    assert result.rate_limit_day.remaining_tokens == 123


async def test_rate_limit_exceeded_by_tokens_per_day(
    mock_tokens_repository, mock_rate_limit_repository, user, usage_limits
):
    mock_rate_limit_repository.get_usage_tier.return_value = usage_limits

    class UsageMock:

        count = 0

        async def usage_function(self, *args, **kwargs):
            if self.count != 3:
                result = RateLimitResult(
                    rate_limited=False,
                    retry_after=None,
                    remaining=123,
                    usage_count=67,
                )
            else:
                result = RateLimitResult(
                    rate_limited=True,
                    retry_after=68400,
                    remaining=0,
                    usage_count=200,
                )
            self.count += 1
            return result

    usage_mock = UsageMock()

    use_case.check_limit_use_case = AsyncMock()
    use_case.check_limit_use_case.execute.side_effect = usage_mock.usage_function
    result = await use_case.execute(
        "model", user, mock_tokens_repository, mock_rate_limit_repository
    )

    assert result.rate_limited is True
    assert result.retry_after == 68400  # Retry after 19h for day-level token limit
    assert result.rate_limit_day.remaining_tokens == 0  # No more tokens available
    assert result.rate_limit_minute.remaining_tokens == 123


async def test_no_rate_limit_on_unlimited_tier(
    mock_tokens_repository, mock_rate_limit_repository, user
):
    usage_tier = UsageLimits(
        model="model",
        max_tokens_per_minute=None,
        max_tokens_per_day=None,
        max_requests_per_minute=None,
        max_requests_per_day=None,
    )
    mock_rate_limit_repository.get_usage_limits_for_model.return_value = usage_tier

    use_case.check_limit_use_case = AsyncMock()
    use_case.check_limit_use_case.execute.return_value = RateLimitResult(
        rate_limited=False,
        retry_after=None,
        remaining=None,
        usage_count=67,
    )
    result = await use_case.execute(
        "model", user, mock_tokens_repository, mock_rate_limit_repository
    )

    assert result.rate_limited is False
    assert result.retry_after is None
    assert result.rate_limit_minute.remaining_requests is None
    assert result.rate_limit_minute.remaining_tokens is None
    assert result.rate_limit_day.remaining_requests is None
    assert result.rate_limit_day.remaining_tokens is None
