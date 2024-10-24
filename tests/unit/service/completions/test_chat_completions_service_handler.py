from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

import distributedinference.service.completions.chat_completions_handler_service as service
from distributedinference.domain.rate_limit.entities import RateLimit
from distributedinference.domain.rate_limit.entities import UserRateLimitResponse
from distributedinference.service.completions.streaming_response import (
    StreamingResponseWithStatusCode,
)
from distributedinference.service.error_responses import RateLimitError


async def test_execute_no_rate_limit():
    # Mock the check_rate_limit function to simulate no rate limit
    rate_limit_result = UserRateLimitResponse(
        rate_limited=False,
        retry_after=None,
        rate_limit_minute=RateLimit(
            max_requests=3,
            max_tokens=1000,
            remaining_requests=99,
            remaining_tokens=999,
            reset_requests=60,
            reset_tokens=60,
        ),
        rate_limit_day=RateLimit(
            max_requests=100,
            max_tokens=10000,
            remaining_requests=999,
            remaining_tokens=9999,
            reset_requests=60,
            reset_tokens=60,
        ),
    )

    with patch(
        "distributedinference.service.completions.chat_completions_handler_service.rate_limit_use_case.execute",
        return_value=rate_limit_result,
    ), patch(
        "distributedinference.service.completions.chat_completions_handler_service.chat_completions_service.execute",
        AsyncMock(),
    ) as mock_service:
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
        assert response.headers["x-ratelimit-remaining-requests"] == "999"
        assert response.headers["x-ratelimit-remaining-tokens"] == "999"
        assert response.headers["x-ratelimit-reset-requests"] == "60s"
        assert response.headers["x-ratelimit-reset-tokens"] == "60s"
        assert "retry-after" not in response.headers
        mock_service.assert_called_once()


async def test_execute_no_rate_limit_stream():
    rate_limit_result = UserRateLimitResponse(
        rate_limited=False,
        retry_after=None,
        rate_limit_minute=RateLimit(
            max_requests=3,
            max_tokens=1000,
            remaining_requests=99,
            remaining_tokens=999,
            reset_requests=60,
            reset_tokens=60,
        ),
        rate_limit_day=RateLimit(
            max_requests=100,
            max_tokens=10000,
            remaining_requests=999,
            remaining_tokens=9999,
            reset_requests=60,
            reset_tokens=60,
        ),
    )

    with patch(
        "distributedinference.service.completions.chat_completions_handler_service.rate_limit_use_case.execute",
        return_value=rate_limit_result,
    ), patch(
        "distributedinference.service.completions.chat_completions_handler_service.chat_completions_stream_service.execute",
        return_value=AsyncMock(),
    ) as mock_stream_service:
        response = MagicMock()
        result = await service.execute(
            request=MagicMock(stream=True),
            response=response,
            user=MagicMock(),
            node_repository=MagicMock(),
            tokens_repository=AsyncMock(),
            rate_limit_repository=AsyncMock(),
            metrics_queue_repository=MagicMock(),
            analytics=AsyncMock(),
        )

        assert isinstance(result, StreamingResponseWithStatusCode)
        assert result.headers["x-ratelimit-limit-requests"] == "100"
        assert result.headers["x-ratelimit-limit-tokens"] == "1000"
        assert result.headers["x-ratelimit-remaining-requests"] == "999"
        assert result.headers["x-ratelimit-remaining-tokens"] == "999"
        assert result.headers["x-ratelimit-reset-requests"] == "60s"
        assert result.headers["x-ratelimit-reset-tokens"] == "60s"
        assert "retry-after" not in result.headers
        mock_stream_service.assert_called_once()


async def test_execute_rate_limited():
    rate_limit_result = UserRateLimitResponse(
        rate_limited=True,
        retry_after=30,
        rate_limit_minute=RateLimit(
            max_requests=3,
            max_tokens=1000,
            remaining_requests=99,
            remaining_tokens=0,
            reset_requests=60,
            reset_tokens=60,
        ),
        rate_limit_day=RateLimit(
            max_requests=100,
            max_tokens=10000,
            remaining_requests=0,
            remaining_tokens=9999,
            reset_requests=60,
            reset_tokens=60,
        ),
    )

    with patch(
        "distributedinference.service.completions.chat_completions_handler_service.rate_limit_use_case.execute",
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


def test_model_name_translation_no_suffix():
    user_input = "llama3.1"
    expected_exact_name = "neuralmagic/Meta-Llama-3.1-8B-Instruct-FP8"
    actual_exact_name = service._match_model_name(user_input)
    assert actual_exact_name == expected_exact_name


def test_model_name_translation_llama3_1_8b():
    user_input = "llama3.1:8b"
    expected_exact_name = "neuralmagic/Meta-Llama-3.1-8B-Instruct-FP8"
    actual_exact_name = service._match_model_name(user_input)
    assert actual_exact_name == expected_exact_name


def test_model_name_translation_llama3_1_70b():
    user_input = "llama3.1:70b"
    expected_exact_name = "neuralmagic/Meta-Llama-3.1-70B-Instruct-quantized.w4a16"
    actual_exact_name = service._match_model_name(user_input)
    assert actual_exact_name == expected_exact_name


def test_model_name_translation_llama3_1_405b():
    user_input = "llama3.1:405b"
    expected_exact_name = "neuralmagic/Meta-Llama-3.1-405B-Instruct-quantized.w4a16"
    actual_exact_name = service._match_model_name(user_input)
    assert actual_exact_name == expected_exact_name


def test_model_name_translation_case_insensitive():
    user_input = "lLaMA3.1:8B"
    expected_exact_name = "neuralmagic/Meta-Llama-3.1-8B-Instruct-FP8"
    actual_exact_name = service._match_model_name(user_input)
    assert actual_exact_name == expected_exact_name


def test_model_name_translation_exact_model():
    user_input = "neuralmagic/Meta-Llama-3.1-405B-Instruct-quantized.w4a16"
    expected_exact_name = "neuralmagic/Meta-Llama-3.1-405B-Instruct-quantized.w4a16"
    actual_exact_name = service._match_model_name(user_input)
    assert actual_exact_name == expected_exact_name
