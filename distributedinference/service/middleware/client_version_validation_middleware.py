from enum import Enum
from typing import NamedTuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from distributedinference.service import error_responses


class SupportedVersionRange(NamedTuple):
    min_version: str
    max_version: str


class Client(str, Enum):
    GPU_NODE = ("gpu-node", SupportedVersionRange("0.0.6", "0.0.6"))

    def __new__(cls, value, version_info):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.min_version = version_info.min_version
        obj.max_version = version_info.max_version
        return obj

    def is_version_supported(self, version: str) -> bool:
        return self.min_version <= version <= self.max_version


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
                raise error_responses.UnsupportedClientError(
                    client_name=client_name,
                    client_version=client_version,
                )

            if not client.is_version_supported(client_version):
                raise error_responses.UnsupportedClientError(
                    client_name=client_name,
                    client_version=client_version,
                )

        return await call_next(request)
