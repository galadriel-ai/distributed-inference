from enum import Enum

from packaging import version
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from distributedinference.service import error_responses


class SupportedVersionRange:
    def __init__(self, min_version: str, max_version: str):
        self.min_version = version.parse(min_version)
        self.max_version = version.parse(max_version)

    def is_version_supported(self, ver: str) -> bool:
        parsed_version = version.parse(ver)
        return self.min_version <= parsed_version <= self.max_version


# pylint: disable=E1120
class Client(str, Enum):
    GPU_NODE = ("gpu-node", SupportedVersionRange("0.0.11", "0.0.16"))

    def __new__(cls, value, version_range):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.version_range = version_range
        return obj


class ClientVersionValidationMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
    ) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        client_version = request.headers.get("client_version")
        client_name = request.headers.get("client_name")

        if client_name and client_version:
            try:
                client = Client(client_name)
            except ValueError:
                raise error_responses.UnsupportedClientError(client_name)

            if not client.version_range.is_version_supported(client_version):
                raise error_responses.UnsupportedClientVersionError(
                    client_name=client_name,
                    client_version=client_version,
                    min_version=client.version_range.min_version,
                )

        return await call_next(request)
