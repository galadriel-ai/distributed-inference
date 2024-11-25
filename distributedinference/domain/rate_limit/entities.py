from decimal import Decimal
from dataclasses import dataclass
from enum import Enum
from typing import List
from typing import Optional
from uuid import UUID


@dataclass
class UsageTier:
    id: UUID
    name: str
    description: Optional[str]


@dataclass
class UsageLimits:
    model: str
    max_tokens_per_minute: Optional[int]
    max_tokens_per_day: Optional[int]
    max_requests_per_minute: Optional[int]
    max_requests_per_day: Optional[int]
    price_per_million_tokens: Optional[Decimal]


@dataclass
class UserUsage(UsageLimits):
    requests_left_day: Optional[int]
    requests_usage_day: Optional[int]
    tokens_left_day: Optional[int]
    tokens_usage_day: Optional[int]
    price_per_million_tokens: Optional[Decimal]


@dataclass
class UserUsageLimitsResponse:
    name: str
    description: Optional[str]
    credits: Optional[Decimal]
    usages: List[UserUsage]


@dataclass
class RateLimitResult:
    rate_limited: bool
    retry_after: Optional[int]
    remaining: Optional[int]
    usage_count: Optional[int]


@dataclass
class RateLimit:
    max_requests: Optional[int]
    max_tokens: Optional[int]
    remaining_requests: Optional[int]
    remaining_tokens: Optional[int]
    reset_requests: Optional[int]
    reset_tokens: Optional[int]


class RateLimitReason(Enum):
    RPM = "RPM"
    RPD = "RPD"
    TPM = "TPM"
    TPD = "TPD"


@dataclass
class UserRateLimitResponse:
    rate_limit_reason: Optional[RateLimitReason]
    retry_after: Optional[int]

    rate_limit_minute: RateLimit
    rate_limit_day: RateLimit
