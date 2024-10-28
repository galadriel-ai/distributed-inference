from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import UUID

from uuid_extensions import uuid7

import settings
from distributedinference.domain.rate_limit.entities import UsageTier
from distributedinference.domain.rate_limit.entities import UserUsage
from distributedinference.domain.rate_limit.entities import UserUsageLimitsResponse
from distributedinference.domain.user.entities import User
from distributedinference.service.rate_limit import rate_limit_service as service
from distributedinference.service.rate_limit.entities import ModelUsage
from distributedinference.service.rate_limit.entities import RateLimitResponse


def _get_usage_tier():
    return UsageTier(
        id=uuid7(),
        name="usage tier",
        description="usage tier description",
    )


async def test_success():
    mock_usage_tier = _get_usage_tier()
    service.get_user_limits_use_case = AsyncMock()
    service.get_user_limits_use_case.execute.return_value = UserUsageLimitsResponse(
        name=mock_usage_tier.name,
        description=mock_usage_tier.description,
        credits=Decimal("0.1"),
        usages=[
            UserUsage(
                model=next(iter(settings.MODEL_NAME_MAPPING.values())),
                max_tokens_per_minute=2,
                max_tokens_per_day=20,
                max_requests_per_minute=1,
                max_requests_per_day=10,
                requests_left_day=9,
                requests_usage_day=1,
                tokens_left_day=18,
                tokens_usage_day=2,
                price_per_million_tokens=Decimal("1.23"),
            ),
            UserUsage(
                model="model_2",
                max_tokens_per_minute=4,
                max_tokens_per_day=40,
                max_requests_per_minute=3,
                max_requests_per_day=30,
                requests_left_day=29,
                requests_usage_day=1,
                tokens_left_day=38,
                tokens_usage_day=2,
                price_per_million_tokens=None,
            ),
        ],
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
        AsyncMock(),
    )
    assert response == RateLimitResponse(
        usage_tier_name=mock_usage_tier.name,
        usage_tier_description=mock_usage_tier.description,
        credits_balance="0.1",
        usages=[
            ModelUsage(
                model=next(iter(settings.MODEL_NAME_MAPPING.keys())),
                full_model=next(iter(settings.MODEL_NAME_MAPPING.values())),
                max_requests_per_day=10,
                max_requests_per_minute=1,
                max_tokens_per_day=20,
                max_tokens_per_minute=2,
                requests_left_day=9,
                requests_used_day=1,
                tokens_left_day=18,
                tokens_used_day=2,
                price_per_million_tokens="1.23",
            ),
            ModelUsage(
                model="model_2",
                full_model="model_2",
                max_requests_per_day=30,
                max_requests_per_minute=3,
                max_tokens_per_day=40,
                max_tokens_per_minute=4,
                requests_left_day=29,
                requests_used_day=1,
                tokens_left_day=38,
                tokens_used_day=2,
                price_per_million_tokens=None,
            ),
        ],
    )
