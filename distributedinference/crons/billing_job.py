from datetime import datetime
from decimal import Decimal
from typing import Dict
from typing import Optional
from uuid import UUID

import settings
from distributedinference import api_logger
from distributedinference.domain.billing.entities import BillableUser
from distributedinference.domain.billing.entities import TotalBill
from distributedinference.repository.billing_repository import BillingRepository
from distributedinference.repository.tokens_repository import TokensRepository

logger = api_logger.get()


class BillingException(Exception):
    pass


# usage_tier_id + model_name: price
# Gets reset on every execution
price_cache: Dict[str, Decimal] = {}


# pylint: disable=W0603
async def execute(
    billing_repository: BillingRepository,
    tokens_repository: TokensRepository,
) -> None:
    global price_cache
    price_cache = {}
    billable_users = await billing_repository.get_billable_users()
    for billable_user in billable_users:
        try:
            user_bill = await _get_user_total_bill(
                billable_user, tokens_repository, billing_repository
            )
            await _bill_user(user_bill, billable_user, billing_repository)
        except Exception:
            logger.error("Unexected error in billing_job", exc_info=True)


async def _get_user_total_bill(
    billable_user: BillableUser,
    tokens_repository: TokensRepository,
    billing_repository: BillingRepository,
) -> TotalBill:
    usages = await tokens_repository.get_grouped_usages_by_time(
        billable_user.user_profile_id, billable_user.last_credit_calculation_at
    )
    total_credits_used = Decimal("0")
    last_credit_calculation_at: Optional[datetime] = None
    for usage in usages:
        model_price = await _get_model_price(billable_user, usage, billing_repository)
        if model_price:
            price = usage.tokens_count * model_price / 1000000
            total_credits_used += price
            if usage.max_created_at:
                if not last_credit_calculation_at:
                    last_credit_calculation_at = usage.max_created_at
                last_credit_calculation_at = max(
                    last_credit_calculation_at, usage.max_created_at
                )
    return TotalBill(
        credits_used=total_credits_used,
        last_credit_calculation_at=last_credit_calculation_at,
    )


async def _get_model_price(
    billable_user, usage, billing_repository
) -> Optional[Decimal]:
    cache_key = f"{billable_user.usage_tier_id}-{usage.model_name}"
    if cache_key in price_cache:
        return price_cache[cache_key]
    model_price = await billing_repository.get_model_price(
        billable_user.usage_tier_id, usage.model_name
    )
    price_cache[cache_key] = model_price
    return model_price


async def _bill_user(
    user_bill: TotalBill,
    billable_user: BillableUser,
    billing_repository: BillingRepository,
) -> None:
    if user_bill.credits_used > Decimal("0"):
        if not user_bill.last_credit_calculation_at:
            logger.error(
                f"Billing error for user: {billable_user.user_profile_id}, failed to get last_credit_calculation_at"
            )
            return
        credits_left = billable_user.credits - user_bill.credits_used
        if credits_left <= Decimal("0"):
            credits_left = Decimal("0")
            await billing_repository.update_user_usage_tier(
                billable_user.user_profile_id, UUID(settings.DEFAULT_USAGE_TIER_UUID)
            )
        await billing_repository.update_user_credits(
            billable_user.user_profile_id,
            credits_left,
            billable_user.currency,
            user_bill.last_credit_calculation_at,
        )
