import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Scope, Receive, Send

from distributedinference.service import error_responses
from distributedinference.service.middleware import util
from distributedinference.service.middleware.entitites import RequestStateKey
from distributedinference.service.middleware.faucet_rate_limit_middleware import (
    IP_RATE_LIMIT_STORE,
    RATE_LIMIT_MINUTES,
    FaucetRateLimitMiddleware,
)


@pytest.fixture
def mock_app():
    async def app(scope, receive, send):
        response = Response("OK", status_code=200)
        await response(scope, receive, send)

    return app


@pytest.fixture
def mock_request():
    scope = {"type": "http", "method": "POST", "path": "/v1/faucet/solana"}
    return Request(scope)


@pytest.fixture
def mock_non_faucet_request():
    scope = {"type": "http", "method": "GET", "path": "/v1/chat"}
    return Request(scope)


def test_init():
    app = MagicMock(spec=ASGIApp)
    middleware = FaucetRateLimitMiddleware(app)
    assert middleware.app == app


@pytest.mark.asyncio
async def test_dispatch_non_faucet_endpoint(mock_app, mock_non_faucet_request):
    middleware = FaucetRateLimitMiddleware(mock_app)

    # Set up the mock request scope with headers
    mock_non_faucet_request.scope["headers"] = [
        (b"host", b"localhost:8000"),
        (b"x-forwarded-for", b"192.168.1.1"),
    ]

    # Set up the IP address in the request state
    util.set_state(mock_non_faucet_request, RequestStateKey.IP_ADDRESS, "192.168.1.1")

    # Create a mock call_next function
    async def mock_call_next(request):
        return Response("OK", status_code=200)

    # Since this isn't the faucet endpoint, it should just call next without rate limiting
    response = await middleware.dispatch(mock_non_faucet_request, mock_call_next)

    assert response.status_code == 200
    assert "192.168.1.1" not in IP_RATE_LIMIT_STORE


@pytest.mark.asyncio
async def test_dispatch_first_request(mock_app, mock_request):
    middleware = FaucetRateLimitMiddleware(mock_app)

    # Clear the rate limit store
    IP_RATE_LIMIT_STORE.clear()

    # Set up the mock request scope with headers
    mock_request.scope["headers"] = [
        (b"host", b"localhost:8000"),
        (b"x-forwarded-for", b"192.168.1.2"),
    ]

    # Set up the IP address in the request state
    test_ip = "192.168.1.2"
    util.set_state(mock_request, RequestStateKey.IP_ADDRESS, test_ip)

    # Create a mock call_next function
    async def mock_call_next(request):
        return Response("OK", status_code=200)

    # First request should pass through
    response = await middleware.dispatch(mock_request, mock_call_next)

    assert response.status_code == 200
    assert test_ip in IP_RATE_LIMIT_STORE


@pytest.mark.asyncio
async def test_dispatch_rate_limited(mock_app, mock_request):
    middleware = FaucetRateLimitMiddleware(mock_app)

    # Clear the rate limit store and add a recent request
    IP_RATE_LIMIT_STORE.clear()
    test_ip = "192.168.1.3"
    IP_RATE_LIMIT_STORE[test_ip] = datetime.now(timezone.utc)

    # Set up the mock request scope with headers
    mock_request.scope["headers"] = [
        (b"host", b"localhost:8000"),
        (b"x-forwarded-for", b"192.168.1.3"),
    ]

    # Set up the IP address in the request state
    util.set_state(mock_request, RequestStateKey.IP_ADDRESS, test_ip)

    # Create a mock call_next function
    async def mock_call_next(request):
        return Response("OK", status_code=200)

    # Second request within rate limit window should be blocked
    with pytest.raises(error_responses.RateLimitError) as exc_info:
        await middleware.dispatch(mock_request, mock_call_next)

    assert f"You can only make one request every {RATE_LIMIT_MINUTES} minutes" in str(
        exc_info.value
    )


@pytest.mark.asyncio
async def test_dispatch_after_rate_limit_expired(mock_app, mock_request):
    middleware = FaucetRateLimitMiddleware(mock_app)

    # Clear the rate limit store and add an old request
    IP_RATE_LIMIT_STORE.clear()
    test_ip = "192.168.1.4"
    IP_RATE_LIMIT_STORE[test_ip] = datetime.now(timezone.utc) - timedelta(
        minutes=RATE_LIMIT_MINUTES + 1
    )

    # Set up the mock request scope with headers
    mock_request.scope["headers"] = [
        (b"host", b"localhost:8000"),
        (b"x-forwarded-for", b"192.168.1.4"),
    ]

    # Set up the IP address in the request state
    util.set_state(mock_request, RequestStateKey.IP_ADDRESS, test_ip)

    # Create a mock call_next function
    async def mock_call_next(request):
        return Response("OK", status_code=200)

    # Request after rate limit window should pass through
    response = await middleware.dispatch(mock_request, mock_call_next)

    assert response.status_code == 200
    assert test_ip in IP_RATE_LIMIT_STORE
    # The timestamp should be updated
    assert (
        datetime.now(timezone.utc) - IP_RATE_LIMIT_STORE[test_ip]
    ).total_seconds() < 1


@pytest.mark.asyncio
async def test_cleanup_old_entries():
    middleware = FaucetRateLimitMiddleware(MagicMock())

    # Clear the rate limit store
    IP_RATE_LIMIT_STORE.clear()

    # Add some entries with different ages
    IP_RATE_LIMIT_STORE["recent"] = datetime.now(timezone.utc)
    IP_RATE_LIMIT_STORE["old"] = datetime.now(timezone.utc) - timedelta(
        hours=25
    )  # older than 24 hours

    # Run cleanup
    middleware._cleanup_old_entries()

    # Verify old entry was removed, recent one remains
    assert "recent" in IP_RATE_LIMIT_STORE
    assert "old" not in IP_RATE_LIMIT_STORE
