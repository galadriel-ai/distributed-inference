from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

import settings
from distributedinference.service import error_responses
from distributedinference.service.middleware import util
from distributedinference.service.middleware.entitites import RequestStateKey


class IpWhitelistMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
    ) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.url.path.startswith("/v1/agents/logs/") and request.method == "POST":
            ip_address = util.get_state(request, RequestStateKey.IP_ADDRESS)
            if not _is_tee_host_ip(ip_address):
                raise error_responses.InvalidCredentialsAPIError()
        return await call_next(request)


def _is_tee_host_ip(ip_address: Optional[str]) -> bool:
    if not settings.is_production():
        return True
    if not ip_address:
        return False
    for base_url in settings.TEE_HOST_BASE_URLS:
        base_url = base_url.replace("http://", "")
        base_url = base_url.replace("https://", "")
        ip = base_url.split(":")[0]
        if ip == ip_address:
            return True
    return False
