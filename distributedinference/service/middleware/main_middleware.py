import time
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from distributedinference import api_logger
from distributedinference.utils import http_headers
from distributedinference.service.error_responses import APIErrorResponse
from distributedinference.service.middleware import util
from distributedinference.service.middleware.entitites import RequestStateKey

logger = api_logger.get()


class MainMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = util.get_state(request, RequestStateKey.REQUEST_ID)
        ip_address = util.get_state(request, RequestStateKey.IP_ADDRESS)
        country = util.get_state(request, RequestStateKey.COUNTRY)

        try:
            logger.info(
                f"REQUEST STARTED "
                f"request_id={request_id} "
                f"request_path={request.url.path} "
                f"ip={ip_address} "
                f"country={country} "
            )
            before = time.time()
            response: Response = await call_next(request)

            process_time = (time.time() - before) * 1000
            formatted_process_time = "{0:.2f}".format(process_time)
            if response.status_code != 404:
                logger.info(
                    f"REQUEST COMPLETED "
                    f"request_id={request_id} "
                    f"request_path={request.url.path} "
                    f"completed_in={formatted_process_time}ms "
                    f"status_code={response.status_code}"
                )
            return await http_headers.add_response_headers(response)
        except Exception as error:
            if isinstance(error, APIErrorResponse):
                is_exc_info = error.to_status_code() == 500
                logger.error(
                    f"Error while handling request. request_id={request_id} "
                    f"request_path={request.url.path}"
                    f"status code={error.to_status_code()}"
                    f"code={error.to_code()}"
                    f"message={error.to_message()}",
                    exc_info=is_exc_info,
                )
            else:
                logger.error(
                    f"Error while handling request. request_id={request_id} "
                    f"request_path={request.url.path}",
                    exc_info=True,
                )
            raise error


# pylint: disable=C2801
def _set_state(request: Request, state_key: RequestStateKey, value: any):
    request.state.__setattr__(state_key.value, value)


def _get_state(request: Request, state_key: RequestStateKey) -> Optional[any]:
    return getattr(request.state, state_key.value, None)
