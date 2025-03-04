from datetime import datetime, timedelta, timezone
import time
from typing import Dict, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

import settings
from distributedinference import api_logger
from distributedinference.service import error_responses
from distributedinference.service.middleware import util
from distributedinference.service.middleware.entitites import RequestStateKey

logger = api_logger.get()

# In-memory storage for rate limiting
# Structure: {ip_address: last_request_timestamp}
IP_RATE_LIMIT_STORE: Dict[str, datetime] = {}

# Rate limit time in minutes from settings
RATE_LIMIT_MINUTES = settings.SOLANA_FAUCET_IP_RATE_LIMIT_MINUTES

# Threshold for cleaning up old entries
CLEANUP_THRESHOLD = 1000

# Time in hours to keep entries in the store
ENTRY_LIFETIME = 24


class FaucetRateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to rate limit faucet requests based on IP address.

    Limits requests to one per IP address every X minutes (configurable).
    Uses an in-memory dictionary for storage.
    """

    def __init__(
        self,
        app: ASGIApp,
    ) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Only apply rate limiting to Solana faucet endpoint
        if request.url.path.endswith("/faucet/solana") and request.method == "POST":
            # Get the original IP address
            ip_address = util.get_state(request, RequestStateKey.IP_ADDRESS)

            # Check if the IP has made a request in the last X minutes
            is_rate_limited = self._check_rate_limit(ip_address)

            if is_rate_limited:
                logger.info(f"Rate limiting Solana faucet request from IP: {ip_address}")
                raise error_responses.RateLimitError(
                    {
                        "error": f"Rate limit exceeded. You can only make one request every {RATE_LIMIT_MINUTES} minutes from the same IP address."
                    }
                )

            # Record this request timestamp
            self._record_request(ip_address)

        return await call_next(request)

    def _check_rate_limit(self, ip_address: str) -> bool:
        """Check if the IP address is rate limited."""
        if ip_address in IP_RATE_LIMIT_STORE:
            last_request_time = IP_RATE_LIMIT_STORE[ip_address]
            now = datetime.now(timezone.utc)
            time_since_last_request = now - last_request_time

            # If the last request was less than RATE_LIMIT_MINUTES ago, rate limit this request
            if time_since_last_request < timedelta(minutes=RATE_LIMIT_MINUTES):
                return True

        return False

    def _record_request(self, ip_address: str) -> None:
        """Record a request from this IP address."""
        IP_RATE_LIMIT_STORE[ip_address] = datetime.now(timezone.utc)

        # Clean up old entries periodically
        if len(IP_RATE_LIMIT_STORE) > CLEANUP_THRESHOLD:
            self._cleanup_old_entries()

    def _cleanup_old_entries(self) -> None:
        """Remove entries older than ENTRY_LIFETIME hours to prevent memory growth."""
        now = datetime.now(timezone.utc)
        expired_time = now - timedelta(hours=ENTRY_LIFETIME)

        # Create a list of IPs to remove
        expired_ips = [
            ip for ip, timestamp in IP_RATE_LIMIT_STORE.items() if timestamp < expired_time
        ]

        # Remove expired entries
        for ip in expired_ips:
            del IP_RATE_LIMIT_STORE[ip]
