from typing import Dict

from distributedinference.domain.rate_limit.entities import UserRateLimitResponse


def rate_limit_to_headers(rate_limit: UserRateLimitResponse) -> Dict[str, str]:
    headers = {
        "x-ratelimit-limit-requests": str(rate_limit.rate_limit_day.max_requests),
        "x-ratelimit-limit-tokens": str(rate_limit.rate_limit_minute.max_tokens or 0),
        "x-ratelimit-remaining-requests": str(
            rate_limit.rate_limit_day.remaining_requests or 0
        ),
        "x-ratelimit-remaining-tokens": str(
            rate_limit.rate_limit_minute.remaining_tokens or 0
        ),
        "x-ratelimit-reset-requests": (
            f"{rate_limit.rate_limit_day.reset_requests}s"
            if rate_limit.rate_limit_day.reset_requests is not None
            else "0s"
        ),
        "x-ratelimit-reset-tokens": (
            f"{rate_limit.rate_limit_minute.reset_tokens}s"
            if rate_limit.rate_limit_minute.reset_tokens is not None
            else "0s"
        ),
    }
    if rate_limit.retry_after:
        headers["retry-after"] = str(rate_limit.retry_after)
    return headers
