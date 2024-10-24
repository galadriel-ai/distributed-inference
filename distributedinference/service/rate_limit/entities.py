from typing import List
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


class ModelUsage(BaseModel):
    model: str = Field("Model name")
    full_model: str = Field("Full model name")
    max_requests_per_day: Optional[int] = Field("Max requests allowed per day")
    max_requests_per_minute: Optional[int] = Field("Max requests allowed per minute")
    max_tokens_per_day: Optional[int] = Field("Max tokens allowed per day")
    max_tokens_per_minute: Optional[int] = Field("Max tokens allowed per minute")

    requests_left_day: Optional[int] = Field("Requests left for the day")
    requests_used_day: Optional[int] = Field("Requests used for the day")
    tokens_left_day: Optional[int] = Field("Tokens left for the day")
    tokens_used_day: Optional[int] = Field("Tokens used for the day")


class RateLimitResponse(BaseModel):
    usage_tier_name: str = Field(description="Current API usage tier name")
    usage_tier_description: str = Field(
        description="Current API usage tier description"
    )
    usages: List[ModelUsage] = Field(description="Model max usage and usage stats")
