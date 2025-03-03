from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

import settings
from distributedinference.domain.rate_limit import get_user_limits_use_case as use_case
from distributedinference.domain.rate_limit.entities import UsageLimits
from distributedinference.domain.rate_limit.entities import UsageTier
from distributedinference.domain.rate_limit.entities import UserUsage
from distributedinference.domain.rate_limit.entities import UserUsageLimitsResponse
from distributedinference.domain.user.entities import User
from distributedinference.repository.billing_repository import BillingRepository
from distributedinference.repository.rate_limit_repository import RateLimitRepository
from distributedinference.repository.tokens_repository import DailyUserModelUsage
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.repository.utils import utctoday
from distributedinference.service import error_responses

PAID_TIER = UUID("0671b61e-518d-7541-8000-49c7ae6bed1b")


def _get_user():
    return User(
        uid=UUID("0671b60d-bdd3-7155-8000-4928322d1265"),
        name="name",
        email="email",
        usage_tier_id=settings.DEFAULT_USAGE_TIER_UUID,
    )


async def test_error():
    tokens_repository = AsyncMock(spec=TokensRepository)
    rate_limit_repository = AsyncMock(spec=RateLimitRepository)
    rate_limit_repository.get_usage_tier_info.return_value = None

    billing_repository = AsyncMock(spec=BillingRepository)

    with pytest.raises(error_responses.NotFoundAPIError) as e:
        await use_case.execute(
            _get_user(), tokens_repository, rate_limit_repository, billing_repository
        )
        assert e is not None


async def test_success():
    tokens_repository = AsyncMock(spec=TokensRepository)
    tokens_repository.get_daily_usage.return_value = DailyUserModelUsage(
        total_requests_count=1,
        total_tokens_count=121,
        model_name="model",
        date=utctoday(),
    )
    rate_limit_repository = AsyncMock(spec=RateLimitRepository)
    rate_limit_repository.get_usage_tier_info.return_value = UsageTier(
        id=PAID_TIER,
        name="mock paid tier",
        description="description",
    )
    rate_limit_repository.get_usage_tier_limits.return_value = [
        UsageLimits(
            model="mock_model",
            max_tokens_per_minute=20,
            max_tokens_per_day=200,
            max_requests_per_minute=10,
            max_requests_per_day=100,
            price_per_million_tokens=Decimal("0.002"),
        )
    ]

    billing_repository = AsyncMock(spec=BillingRepository)
    billing_repository.get_user_credit_balance.return_value = Decimal("0.2")

    response = await use_case.execute(
        _get_user(), tokens_repository, rate_limit_repository, billing_repository
    )
    assert response == UserUsageLimitsResponse(
        name="mock paid tier",
        description="description",
        credits=Decimal("0.2"),
        usages=[
            UserUsage(
                model="mock_model",
                max_tokens_per_minute=20,
                max_tokens_per_day=200,
                max_requests_per_minute=10,
                max_requests_per_day=100,
                requests_left_day=99,
                requests_usage_day=1,
                tokens_left_day=79,
                tokens_usage_day=121,
                price_per_million_tokens=Decimal("0.002"),
            )
        ],
    )
