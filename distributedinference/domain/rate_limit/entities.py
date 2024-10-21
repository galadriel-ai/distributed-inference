from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class UsageTier:
    id: UUID
    name: str
    description: Optional[str]
    max_tokens_per_minute: Optional[int]
    max_tokens_per_day: Optional[int]
    max_requests_per_minute: Optional[int]
    max_requests_per_day: Optional[int]
    created_at: datetime
    last_updated_at: datetime


@dataclass
class RateLimitResult:
    rate_limited: bool
    retry_after: Optional[int]
    remaining: Optional[int]


@dataclass
class RateLimit:
    max_requests: Optional[int]
    max_tokens: Optional[int]
    remaining_requests: Optional[int]
    remaining_tokens: Optional[int]
    reset_requests: Optional[int]
    reset_tokens: Optional[int]


@dataclass
class UserRateLimitResponse:
    usage_tier: UsageTier

    rate_limited: bool
    retry_after: Optional[int]

    rate_limit_minute: RateLimit
    rate_limit_day: RateLimit
    # TODO: include usage_tier
