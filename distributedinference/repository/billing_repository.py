from datetime import datetime
from decimal import Decimal
from typing import List
from typing import Optional
from uuid import UUID

import sqlalchemy
from uuid_extensions import uuid7

from distributedinference.domain.billing.entities import BillableUser
from distributedinference.repository.connection import SessionProvider
from distributedinference.repository.utils import utcnow

SQL_ADD_CREDITS = """
INSERT INTO user_credits (
    id,
    user_profile_id,
    credits,
    currency,
    last_credit_calculation_at,
    created_at,
    last_updated_at
) VALUES (
    :id,
    :user_profile_id,
    :credits,
    :currency,
    :last_credit_calculation_at,
    :created_at,
    :last_updated_at
) ON CONFLICT (user_profile_id, currency) DO UPDATE SET
    credits = user_credits.credits + EXCLUDED.credits,
    last_updated_at = EXCLUDED.last_updated_at;
"""

SQL_UPDATE_CREDITS = """
UPDATE user_credits
SET 
    credits = :credits,
    last_credit_calculation_at = :last_credit_calculation_at,
    last_updated_at = :last_updated_at
WHERE 
    user_profile_id = :user_profile_id
    AND currency = :currency;
"""

SQL_UPDATE_USER_USAGE_TIER = """
UPDATE user_profile
SET
    usage_tier_id = :usage_tier_id,
    last_updated_at = :last_updated_at
WHERE id = :user_profile_id;
"""

SQL_GET_GET_USER_CREDITS = """
SELECT
    credits
FROM user_credits
WHERE user_profile_id = :user_profile_id;
"""

SQL_GET_BILLABLE_USERS = """
SELECT
    up.id AS user_profile_id,
    uc.credits,
    uc.currency,
    uc.last_credit_calculation_at,
    up.usage_tier_id
FROM user_credits uc
LEFT JOIN user_profile up on uc.user_profile_id = up.id
WHERE uc.credits > 0
AND exists(
    SELECT
        id
    FROM usage_tokens
    WHERE
        consumer_user_profile_id = uc.user_profile_id
        AND usage_tokens.created_at > uc.last_credit_calculation_at
);
"""

SQL_GET_MODEL_PRICE = """
SELECT
    price_per_million_tokens
FROM usage_limit
WHERE 
    usage_tier_id = :usage_tier_id
    AND model_name = :model_name;
"""


class BillingRepository:

    def __init__(
        self, session_provider: SessionProvider, session_provider_read: SessionProvider
    ):
        self._session_provider = session_provider
        self._session_provider_read = session_provider_read

    async def add_credits(
        self, user_id: UUID, credits_amount: Decimal, currency: str = "usd"
    ):
        """
        ONLY used for adding credits to users
        """
        data = {
            "id": uuid7(),
            "user_profile_id": user_id,
            "credits": credits_amount,
            "currency": currency,
            "last_credit_calculation_at": utcnow(),
            "created_at": utcnow(),
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_ADD_CREDITS), data)
            await session.commit()

    async def update_user_credits(
        self,
        user_profile_id,
        credits_amount: Decimal,
        currency: str,
        last_credit_calculation_at: datetime,
    ):
        data = {
            "user_profile_id": user_profile_id,
            "credits": credits_amount,
            "currency": currency,
            "last_credit_calculation_at": last_credit_calculation_at,
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_UPDATE_CREDITS), data)
            await session.commit()

    async def update_user_usage_tier(
        self, user_profile_id: UUID, usage_tier_id: UUID
    ) -> None:
        data = {
            "user_profile_id": user_profile_id,
            "usage_tier_id": usage_tier_id,
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_UPDATE_USER_USAGE_TIER), data)
            await session.commit()

    async def get_user_credit_balance(self, user_profile_id: UUID) -> Optional[Decimal]:
        data = {"user_profile_id": user_profile_id}
        async with self._session_provider_read.get() as session:
            result = await session.execute(
                sqlalchemy.text(SQL_GET_GET_USER_CREDITS), data
            )
            row = result.first()
            if row:
                return row.credits
        return None

    async def get_billable_users(self) -> List[BillableUser]:
        data = {}
        results = []
        async with self._session_provider_read.get() as session:
            rows = await session.execute(sqlalchemy.text(SQL_GET_BILLABLE_USERS), data)
            for row in rows:
                results.append(
                    BillableUser(
                        user_profile_id=row.user_profile_id,
                        usage_tier_id=row.usage_tier_id,
                        credits=row.credits,
                        currency=row.currency,
                        last_credit_calculation_at=row.last_credit_calculation_at,
                    )
                )
        return results

    async def get_model_price(
        self, usage_tier_id: UUID, model: str
    ) -> Optional[Decimal]:
        data = {
            "usage_tier_id": usage_tier_id,
            "model_name": model,
        }
        async with self._session_provider_read.get() as session:
            result = await session.execute(sqlalchemy.text(SQL_GET_MODEL_PRICE), data)
            row = result.first()
            if row:
                return row.price_per_million_tokens
        return None
