import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import distributedinference.service.completions.chat_completions_handler_service as service
from distributedinference.service.completions.entities import RateLimit
from distributedinference.service.error_responses import RateLimitError


async def test_execute_no_rate_limit():
    # Mock the check_rate_limit function to simulate no rate limit
    rate_limit_result = RateLimit(
        rate_limited=False,
        retry_after=None,
        rate_limit_requests=100,
        rate_limit_tokens=1000,
        rate_limit_remaining_requests=99,
        rate_limit_remaining_tokens=999,
        rate_limit_reset_requests=60,
        rate_limit_reset_tokens=60,
    )

    with patch(
        "distributedinference.service.completions.chat_completions_handler_service.check_rate_limit",
        return_value=rate_limit_result,
    ), patch(
        "distributedinference.service.completions.chat_completions_handler_service.chat_completions_service.execute",
        AsyncMock(),
    ):
        response = MagicMock(headers={})
        await service.execute(
            request=MagicMock(stream=False),
            response=response,
            user=MagicMock(),
            node_repository=MagicMock(),
            tokens_repository=AsyncMock(),
            rate_limit_repository=AsyncMock(),
            metrics_queue_repository=MagicMock(),
            analytics=AsyncMock(),
        )

        assert response.headers["x-ratelimit-limit-requests"] == "100"
        assert response.headers["x-ratelimit-limit-tokens"] == "1000"
        assert response.headers["x-ratelimit-remaining-requests"] == "99"
        assert response.headers["x-ratelimit-remaining-tokens"] == "999"
        assert response.headers["x-ratelimit-reset-requests"] == "60s"
        assert response.headers["x-ratelimit-reset-tokens"] == "60s"
        assert "retry-after" not in response.headers


async def test_execute_rate_limited():
    rate_limit_result = RateLimit(
        rate_limited=True,
        retry_after=30,
        rate_limit_requests=100,
        rate_limit_tokens=1000,
        rate_limit_remaining_requests=0,
        rate_limit_remaining_tokens=0,
        rate_limit_reset_requests=60,
        rate_limit_reset_tokens=60,
    )

    with patch(
        "distributedinference.service.completions.chat_completions_handler_service.check_rate_limit",
        return_value=rate_limit_result,
    ):
        response = MagicMock()
        with pytest.raises(RateLimitError) as exc_info:
            await service.execute(
                request=MagicMock(),
                response=response,
                user=MagicMock(),
                node_repository=MagicMock(),
                tokens_repository=AsyncMock(),
                rate_limit_repository=AsyncMock(),
                metrics_queue_repository=MagicMock(),
                analytics=AsyncMock(),
            )

        assert "retry-after" in exc_info.value.headers
        assert exc_info.value.headers["retry-after"] == "30"
        assert exc_info.value.headers["x-ratelimit-limit-requests"] == "100"
        assert exc_info.value.headers["x-ratelimit-limit-tokens"] == "1000"
        assert exc_info.value.headers["x-ratelimit-remaining-requests"] == "0"
        assert exc_info.value.headers["x-ratelimit-remaining-tokens"] == "0"
        assert exc_info.value.headers["x-ratelimit-reset-requests"] == "60s"
        assert exc_info.value.headers["x-ratelimit-reset-tokens"] == "60s"
