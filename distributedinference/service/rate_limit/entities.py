from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class RateLimit(BaseModel):
    rate_limited: bool = Field(
        description="Whether the request was rate limited.",
        default=False,
    )
    retry_after: Optional[int] = Field(
        description="The number of seconds to wait before retrying the request.",
        default=None,
    )
    rate_limit_requests: Optional[int] = Field(
        description="The number of requests that can be made in the current time window.",
        default=None,
    )
    rate_limit_tokens: Optional[int] = Field(
        description="The number of tokens that can be used in the current time window.",
        default=None,
    )
    rate_limit_remaining_requests: Optional[int] = Field(
        description="The number of requests that can still be made in the current time window.",
        default=None,
    )
    rate_limit_remaining_tokens: Optional[int] = Field(
        description="The number of tokens that can still be used in the current time window.",
        default=None,
    )
    rate_limit_reset_requests: Optional[int] = Field(
        description="The number of seconds until the rate limit (based on requests) resets.",
        default=None,
    )
    rate_limit_reset_tokens: Optional[int] = Field(
        description="The number of seconds until the rate limit (based on tokens) resets.",
        default=None,
    )
