import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timedelta, timezone
from uuid import UUID

from uuid_extensions import uuid7

from distributedinference.domain.user.entities import User
from distributedinference.repository.tokens_repository import UsageInformation
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.repository.rate_limit_repository import UsageTier
from distributedinference.repository.rate_limit_repository import RateLimitRepository
from distributedinference.service.completions.rate_limit import check_rate_limit


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
def usage_tier():
    return UsageTier(
        id=UUID("06706644-2409-7efd-8000-3371c5d632d3"),
        name="mock_tier",
        description="mock_description",
        max_requests_per_minute=3,
        max_requests_per_day=100,
        max_tokens_per_minute=1000,
        max_tokens_per_day=10000,
        created_at=datetime.now(),
        last_updated_at=datetime.now(),
    )


async def test_rate_limit_not_exceeded(
    mock_tokens_repository, mock_rate_limit_repository, user, usage_tier
):
    mock_rate_limit_repository.get_usage_tier.return_value = usage_tier
    mock_tokens_repository.get_requests_usage_by_time_and_consumer.return_value = (
        UsageInformation(count=0, oldest_usage_id=None, oldest_usage_created_at=None)
    )
    mock_tokens_repository.get_tokens_usage_by_time_and_consumer.return_value = (
        UsageInformation(count=0, oldest_usage_id=None, oldest_usage_created_at=None)
    )

    result = await check_rate_limit(
        user, mock_tokens_repository, mock_rate_limit_repository
    )

    assert result.rate_limited is False
    assert result.retry_after is None
    assert result.rate_limit_remaining_requests == 3
    assert result.rate_limit_remaining_tokens == 1000


async def test_rate_limit_exceeded_by_requests_per_minute(
    mock_tokens_repository, mock_rate_limit_repository, user, usage_tier
):
    mock_rate_limit_repository.get_usage_tier.return_value = usage_tier

    oldest_usage_time_minute = datetime.now(timezone.utc) - timedelta(seconds=50)
    oldest_usage_time_day = datetime.now(timezone.utc) - timedelta(hours=23, minutes=59)
    mock_tokens_repository.get_requests_usage_by_time_and_consumer.side_effect = [
        # First call for minute limit (exceeds limit)
        UsageInformation(
            count=3,
            oldest_usage_id=uuid7(),
            oldest_usage_created_at=oldest_usage_time_minute,
        ),
        # Second call for day limit (within limit)
        UsageInformation(
            count=50,
            oldest_usage_id=uuid7(),
            oldest_usage_created_at=oldest_usage_time_day,
        ),
    ]
    # Tokens are within the limit for both minute and day
    mock_tokens_repository.get_tokens_usage_by_time_and_consumer.side_effect = [
        UsageInformation(
            count=100,
            oldest_usage_id=uuid7(),
            oldest_usage_created_at=oldest_usage_time_minute,
        ),
        UsageInformation(
            count=5000,
            oldest_usage_id=uuid7(),
            oldest_usage_created_at=oldest_usage_time_day,
        ),
    ]

    result = await check_rate_limit(
        user, mock_tokens_repository, mock_rate_limit_repository
    )

    assert result.rate_limited is True
    assert result.retry_after == 9  # Retry after 9 seconds for minute-level limit
    assert result.rate_limit_remaining_requests == 0


async def test_rate_limit_exceeded_by_requests_per_day(
    mock_tokens_repository, mock_rate_limit_repository, user, usage_tier
):
    mock_rate_limit_repository.get_usage_tier.return_value = usage_tier

    oldest_usage_time_minute = datetime.now(timezone.utc) - timedelta(seconds=30)
    oldest_usage_time_day = datetime.now(timezone.utc) - timedelta(hours=23, minutes=59)
    mock_tokens_repository.get_requests_usage_by_time_and_consumer.side_effect = [
        # First call for minute limit (within limit)
        UsageInformation(
            count=2,
            oldest_usage_id=uuid7(),
            oldest_usage_created_at=oldest_usage_time_minute,
        ),
        # Second call for day limit (exceeded)
        UsageInformation(
            count=100,
            oldest_usage_id=uuid7(),
            oldest_usage_created_at=oldest_usage_time_day,
        ),
    ]
    # Tokens are within the limit for both minute and day
    mock_tokens_repository.get_tokens_usage_by_time_and_consumer.side_effect = [
        UsageInformation(
            count=200,
            oldest_usage_id=uuid7(),
            oldest_usage_created_at=oldest_usage_time_minute,
        ),
        UsageInformation(
            count=8000,
            oldest_usage_id=uuid7(),
            oldest_usage_created_at=oldest_usage_time_day,
        ),
    ]

    result = await check_rate_limit(
        user, mock_tokens_repository, mock_rate_limit_repository
    )

    assert result.rate_limited is True
    assert result.retry_after == 59  # Retry after 59 seconds for day-level limit
    assert result.rate_limit_remaining_requests == 0  # No more requests available


async def test_rate_limit_exceeded_by_tokens_per_minute(
    mock_tokens_repository, mock_rate_limit_repository, user, usage_tier
):
    mock_rate_limit_repository.get_usage_tier.return_value = usage_tier

    oldest_usage_time_minute = datetime.now(timezone.utc) - timedelta(seconds=30)
    oldest_usage_time_day = datetime.now(timezone.utc) - timedelta(hours=5)
    mock_tokens_repository.get_requests_usage_by_time_and_consumer.side_effect = [
        # Requests within minute limit
        UsageInformation(
            count=1,
            oldest_usage_id=uuid7(),
            oldest_usage_created_at=oldest_usage_time_minute,
        ),
        # Requests within day limit
        UsageInformation(
            count=50,
            oldest_usage_id=uuid7(),
            oldest_usage_created_at=oldest_usage_time_day,
        ),
    ]
    mock_tokens_repository.get_tokens_usage_by_time_and_consumer.side_effect = [
        # Tokens exceeding minute limit (1500 tokens in 1 minute with a limit of 1000)
        UsageInformation(
            count=1500,
            oldest_usage_id=uuid7(),
            oldest_usage_created_at=oldest_usage_time_minute,
        ),
        # Tokens within day limit (e.g., 5000 tokens in a day with a limit of 10000)
        UsageInformation(
            count=5000,
            oldest_usage_id=uuid7(),
            oldest_usage_created_at=oldest_usage_time_day,
        ),
    ]

    result = await check_rate_limit(
        user, mock_tokens_repository, mock_rate_limit_repository
    )

    assert result.rate_limited is True
    assert (
        result.retry_after == 29
    )  # Retry after remaining 29 seconds for the minute-level token limit
    assert result.rate_limit_remaining_tokens == 0


async def test_rate_limit_exceeded_by_tokens_per_day(
    mock_tokens_repository, mock_rate_limit_repository, user, usage_tier
):
    mock_rate_limit_repository.get_usage_tier.return_value = usage_tier

    oldest_usage_time_minute = datetime.now(timezone.utc) - timedelta(seconds=30)
    oldest_usage_time_day = datetime.now(timezone.utc) - timedelta(hours=23, minutes=59)
    mock_tokens_repository.get_requests_usage_by_time_and_consumer.side_effect = [
        # Requests within minute limit
        UsageInformation(
            count=2,
            oldest_usage_id=uuid7(),
            oldest_usage_created_at=oldest_usage_time_minute,
        ),
        # Requests within day limit
        UsageInformation(
            count=50,
            oldest_usage_id=uuid7(),
            oldest_usage_created_at=oldest_usage_time_day,
        ),
    ]

    # Tokens within the minute limit
    mock_tokens_repository.get_tokens_usage_by_time_and_consumer.side_effect = [
        UsageInformation(
            count=100,
            oldest_usage_id=uuid7(),
            oldest_usage_created_at=oldest_usage_time_minute,
        ),
        # Exceeding the day limit
        UsageInformation(
            count=10000,
            oldest_usage_id=uuid7(),
            oldest_usage_created_at=oldest_usage_time_day,
        ),
    ]

    result = await check_rate_limit(
        user, mock_tokens_repository, mock_rate_limit_repository
    )

    assert result.rate_limited is True
    assert result.retry_after == 59  # Retry after 59 seconds for tokens
    assert result.rate_limit_remaining_tokens == 0  # No more tokens available


async def test_no_rate_limit_on_unlimited_tier(
    mock_tokens_repository, mock_rate_limit_repository, user
):
    usage_tier = UsageTier(
        id=UUID("06706644-2409-7efd-8000-3371c5d632d3"),
        name="mock_tier",
        description="mock_description",
        max_requests_per_minute=None,
        max_requests_per_day=None,
        max_tokens_per_minute=None,
        max_tokens_per_day=None,
        created_at=datetime.now(),
        last_updated_at=datetime.now(),
    )
    mock_rate_limit_repository.get_usage_tier.return_value = usage_tier

    mock_tokens_repository.get_requests_usage_by_time_and_consumer.return_value = (
        UsageInformation(
            count=100000,
            oldest_usage_id=uuid7(),
            oldest_usage_created_at=datetime.now(),
        )
    )
    mock_tokens_repository.get_tokens_usage_by_time_and_consumer.return_value = (
        UsageInformation(
            count=100000,
            oldest_usage_id=uuid7(),
            oldest_usage_created_at=datetime.now(),
        )
    )

    result = await check_rate_limit(
        user, mock_tokens_repository, mock_rate_limit_repository
    )

    assert result.rate_limited is False
    assert result.retry_after is None
    assert result.rate_limit_remaining_requests is None
    assert result.rate_limit_remaining_tokens is None
