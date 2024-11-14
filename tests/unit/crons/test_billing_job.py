from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import UUID

import settings
from distributedinference.crons import billing_job as job
from distributedinference.domain.billing.entities import BillableUser
from distributedinference.repository.billing_repository import BillingRepository
from distributedinference.repository.tokens_repository import ModelUsageInformation
from distributedinference.repository.tokens_repository import TokensRepository

USER_ID_0 = UUID("0671b45a-d2c5-7996-8000-99cfb694762d")
USER_ID_1 = UUID("0671b4cd-4be7-7a41-8000-e428044b4c4e")

USAGE_TIER_FREE = settings.DEFAULT_USAGE_TIER_UUID
USAGE_TIER_PAID = UUID("0671b45c-9df1-75c6-8000-057ff87ed140")

MODELS = [
    "model-0",
    "model-1",
    "model-2",
]


async def _get_model_price(usage_tier: UUID, model_name: str):
    if usage_tier != USAGE_TIER_PAID:
        return None
    if model_name == MODELS[0]:
        return Decimal("0.5")
    elif model_name == MODELS[1]:
        return Decimal("0.1")
    elif model_name == MODELS[2]:
        return Decimal("1")
    return None


async def _get_grouped_usages_by_time_error(user_profile_id: UUID, date: datetime):
    if user_profile_id == USER_ID_0:
        raise Exception("asd")
    return [
        ModelUsageInformation(
            model_name=MODELS[0],
            tokens_count=1_000_000,
            max_created_at=datetime(2024, 1, 2),
        )
    ]


async def _get_grouped_usages_by_time_no_date(user_profile_id: UUID, date: datetime):
    if user_profile_id == USER_ID_0:
        return [
            ModelUsageInformation(
                model_name=MODELS[0],
                tokens_count=1_000_000,
                max_created_at=None,
            )
        ]
    return [
        ModelUsageInformation(
            model_name=MODELS[0],
            tokens_count=1_000_000,
            max_created_at=datetime(2024, 1, 2),
        )
    ]


async def test_no_bills():
    billing_repository = AsyncMock(spec=BillingRepository)
    billing_repository.get_billable_users.return_value = []

    tokens_repository = AsyncMock(spec=TokensRepository)

    await job.execute(billing_repository, tokens_repository)
    tokens_repository.get_grouped_usages_by_time.assert_not_called()
    assert job.price_cache == {}


async def test_one_user_one_model():
    billing_repository = AsyncMock(spec=BillingRepository)
    billing_repository.get_billable_users.return_value = [
        BillableUser(
            user_profile_id=USER_ID_0,
            usage_tier_id=USAGE_TIER_PAID,
            credits=Decimal("1"),
            currency="usd",
            last_credit_calculation_at=datetime(2024, 1, 1),
        )
    ]
    billing_repository.get_model_price.return_value = Decimal("0.5")

    tokens_repository = AsyncMock(spec=TokensRepository)
    tokens_repository.get_grouped_usages_by_time.return_value = [
        ModelUsageInformation(
            model_name=MODELS[0],
            tokens_count=1_000_000,
            max_created_at=datetime(2024, 1, 2),
        )
    ]

    await job.execute(billing_repository, tokens_repository)
    billing_repository.update_user_credits.assert_called_with(
        USER_ID_0,
        Decimal("0.5"),
        "usd",
        datetime(2024, 1, 2),
    )


async def test_one_user_multiple_models():
    billing_repository = AsyncMock(spec=BillingRepository)
    billing_repository.get_billable_users.return_value = [
        BillableUser(
            user_profile_id=USER_ID_0,
            usage_tier_id=USAGE_TIER_PAID,
            credits=Decimal("1"),
            currency="usd",
            last_credit_calculation_at=datetime(2024, 1, 1),
        )
    ]
    billing_repository.get_model_price = AsyncMock(side_effect=_get_model_price)

    tokens_repository = AsyncMock(spec=TokensRepository)
    tokens_repository.get_grouped_usages_by_time.return_value = [
        ModelUsageInformation(
            model_name=MODELS[0],
            tokens_count=1_000_000,
            max_created_at=datetime(2024, 1, 2),
        ),
        ModelUsageInformation(
            model_name=MODELS[1],
            tokens_count=1_000_000,
            max_created_at=datetime(2024, 1, 2),
        ),
        ModelUsageInformation(
            model_name="free-model",
            tokens_count=1_000_000,
            max_created_at=datetime(2024, 1, 2),
        ),
    ]

    await job.execute(billing_repository, tokens_repository)

    billing_repository.update_user_usage_tier.assert_not_called()
    billing_repository.update_user_credits.assert_called_with(
        USER_ID_0,
        Decimal("0.4"),  # 0.5 for MODELS[0] and 0.1 for MODELS[1]
        "usd",
        datetime(2024, 1, 2),
    )


async def test_user_runs_out_of_credits_tier_updated():
    billing_repository = AsyncMock(spec=BillingRepository)
    billing_repository.get_billable_users.return_value = [
        BillableUser(
            user_profile_id=USER_ID_0,
            usage_tier_id=USAGE_TIER_PAID,
            credits=Decimal("1"),
            currency="usd",
            last_credit_calculation_at=datetime(2024, 1, 1),
        )
    ]
    billing_repository.get_model_price = AsyncMock(side_effect=_get_model_price)

    tokens_repository = AsyncMock(spec=TokensRepository)
    tokens_repository.get_grouped_usages_by_time.return_value = [
        ModelUsageInformation(
            model_name=MODELS[0],
            tokens_count=1_000_000,
            max_created_at=datetime(2024, 1, 2),
        ),
        ModelUsageInformation(
            model_name=MODELS[1],
            tokens_count=5_000_000,
            max_created_at=datetime(2024, 1, 3),
        ),
    ]

    await job.execute(billing_repository, tokens_repository)

    billing_repository.update_user_usage_tier.assert_called_with(
        USER_ID_0, UUID(settings.DEFAULT_USAGE_TIER_UUID)
    )
    billing_repository.update_user_credits.assert_called_with(
        USER_ID_0,
        Decimal("0"),  # 0.5 for MODELS[0] and 0.1 for MODELS[1]
        "usd",
        datetime(2024, 1, 3),  # Uses latest date!
    )


async def test_two_users_success():
    billing_repository = AsyncMock(spec=BillingRepository)
    billing_repository.get_billable_users.return_value = [
        BillableUser(
            user_profile_id=USER_ID_0,
            usage_tier_id=USAGE_TIER_PAID,
            credits=Decimal("1"),
            currency="usd",
            last_credit_calculation_at=datetime(2024, 1, 1),
        ),
        BillableUser(
            user_profile_id=USER_ID_1,
            usage_tier_id=USAGE_TIER_PAID,
            credits=Decimal("1"),
            currency="usd",
            last_credit_calculation_at=datetime(2024, 1, 1),
        ),
    ]
    billing_repository.get_model_price.return_value = Decimal("0.5")

    tokens_repository = AsyncMock(spec=TokensRepository)
    tokens_repository.get_grouped_usages_by_time.return_value = [
        ModelUsageInformation(
            model_name=MODELS[0],
            tokens_count=1_000_000,
            max_created_at=datetime(2024, 1, 2),
        )
    ]

    await job.execute(billing_repository, tokens_repository)
    call_args = billing_repository.update_user_credits.await_args_list

    assert call_args[0].args == (
        USER_ID_0,
        Decimal("0.5"),
        "usd",
        datetime(2024, 1, 2),
    )
    assert call_args[1].args == (
        USER_ID_1,
        Decimal("0.5"),
        "usd",
        datetime(2024, 1, 2),
    )
    billing_repository.get_model_price.assert_called_once()


async def test_one_user_exception_one_succeeds():
    billing_repository = AsyncMock(spec=BillingRepository)
    billing_repository.get_billable_users.return_value = [
        BillableUser(
            user_profile_id=USER_ID_0,
            usage_tier_id=USAGE_TIER_PAID,
            credits=Decimal("1"),
            currency="usd",
            last_credit_calculation_at=datetime(2024, 1, 1),
        ),
        BillableUser(
            user_profile_id=USER_ID_1,
            usage_tier_id=USAGE_TIER_PAID,
            credits=Decimal("1"),
            currency="usd",
            last_credit_calculation_at=datetime(2024, 1, 1),
        ),
    ]
    billing_repository.get_model_price.return_value = Decimal("0.5")

    tokens_repository = AsyncMock(spec=TokensRepository)
    tokens_repository.get_grouped_usages_by_time = AsyncMock(
        side_effect=_get_grouped_usages_by_time_error
    )

    await job.execute(billing_repository, tokens_repository)
    billing_repository.update_user_credits.assert_called_with(
        USER_ID_1,
        Decimal("0.5"),
        "usd",
        datetime(2024, 1, 2),
    )


async def test_one_user_no_date_one_succeeds():
    # Ultimate edge-case, should not really be possible
    billing_repository = AsyncMock(spec=BillingRepository)
    billing_repository.get_billable_users.return_value = [
        BillableUser(
            user_profile_id=USER_ID_0,
            usage_tier_id=USAGE_TIER_PAID,
            credits=Decimal("1"),
            currency="usd",
            last_credit_calculation_at=datetime(2024, 1, 1),
        ),
        BillableUser(
            user_profile_id=USER_ID_1,
            usage_tier_id=USAGE_TIER_PAID,
            credits=Decimal("1"),
            currency="usd",
            last_credit_calculation_at=datetime(2024, 1, 1),
        ),
    ]
    billing_repository.get_model_price.return_value = Decimal("0.5")

    tokens_repository = AsyncMock(spec=TokensRepository)
    tokens_repository.get_grouped_usages_by_time = AsyncMock(
        side_effect=_get_grouped_usages_by_time_no_date
    )

    await job.execute(billing_repository, tokens_repository)
    billing_repository.update_user_credits.assert_called_with(
        USER_ID_1,
        Decimal("0.5"),
        "usd",
        datetime(2024, 1, 2),
    )
