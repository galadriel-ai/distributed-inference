from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class BillableUser:
    user_profile_id: UUID
    usage_tier_id: UUID
    credits: Decimal
    currency: str
    last_credit_calculation_at: datetime


@dataclass(frozen=True)
class TotalBill:
    credits_used: Decimal
    last_credit_calculation_at: Optional[datetime]


@dataclass
class CreditsReport:
    user_profile_id: UUID
    email: str
    credits: Decimal
    latest_credits_addition: Decimal
    percentage_left: Optional[Decimal] = None
