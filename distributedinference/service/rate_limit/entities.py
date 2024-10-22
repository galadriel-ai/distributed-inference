from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class SingleRateLimit(BaseModel):
    max_requests: Optional[int] = Field(
        description="The number of requests that can be made in the current time window.",
        default=None,
    )
    max_tokens: Optional[int] = Field(
        description="The number of tokens that can be used in the current time window.",
        default=None,
    )
    remaining_requests: Optional[int] = Field(
        description="The number of requests that can still be made in the current time window.",
        default=None,
    )
    remaining_tokens: Optional[int] = Field(
        description="The number of tokens that can still be used in the current time window.",
        default=None,
    )
    reset_requests: Optional[int] = Field(
        description="The number of seconds until the rate limit (based on requests) resets.",
        default=None,
    )
    reset_tokens: Optional[int] = Field(
        description="The number of seconds until the rate limit (based on tokens) resets.",
        default=None,
    )


class RateLimitResponse(BaseModel):
    usage_tier_name: str = Field(description="Current API usage tier name")
    usage_tier_description: str = Field(
        description="Current API usage tier description"
    )
    rate_limited: bool = Field(
        description="Whether the request was rate limited.",
        default=False,
    )
    retry_after: Optional[int] = Field(
        description="The number of seconds to wait before retrying the request.",
        default=None,
    )
    rate_limit_minute: SingleRateLimit = Field(description="Second based rate limits")
    rate_limit_day: SingleRateLimit = Field(description="Day based rate limits")
