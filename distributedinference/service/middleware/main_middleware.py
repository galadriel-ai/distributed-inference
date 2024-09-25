import time
from typing import Any
from typing import Optional

from prometheus_client import Counter

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from distributedinference import api_logger
from distributedinference import dependencies
from distributedinference.analytics.analytics import (
    AnalyticsEvent,
    EventName,
)
from distributedinference.domain.node.entities import InferenceStatusCodes
from distributedinference.utils import http_headers
from distributedinference.service.error_responses import APIErrorResponse
from distributedinference.service.middleware import util
from distributedinference.service.middleware.entitites import RequestStateKey

logger = api_logger.get()

response_status_codes_counter = Counter(
    "response_status_codes",
    "Total number of HTTP status codes of each endpoint",
    ["endpoint", "status_code"],
)


class MainMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = util.get_state(request, RequestStateKey.REQUEST_ID)
        ip_address = util.get_state(request, RequestStateKey.IP_ADDRESS)
        country = util.get_state(request, RequestStateKey.COUNTRY)
        analytics = dependencies.get_analytics()

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
            user_id = util.get_state(request, RequestStateKey.USER_ID)

            response_status_codes_counter.labels(
                request.url.path, response.status_code
            ).inc()
            analytics.track_event(
                user_id,
                AnalyticsEvent(
                    EventName.API_RESPONSE,
                    {"request_id": request_id, "status_code": response.status_code},
                ),
            )

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

                error_status_code = error.to_status_code()
                response_status_codes_counter.labels(
                    request.url.path, error_status_code
                ).inc()

                user_id = util.get_state(request, RequestStateKey.USER_ID)
                if user_id:
                    analytics.track_event(
                        user_id,
                        AnalyticsEvent(
                            EventName.API_RESPONSE,
                            {
                                "request_id": request_id,
                                "status_code": error_status_code,
                            },
                        ),
                    )

                is_exc_info = error_status_code == 500
                logger.error(
                    f"Error while handling request. request_id={request_id} "
                    f"request_path={request.url.path} "
                    f"status code={error.to_status_code()} "
                    f"code={error.to_code()} "
                    f"message={error.to_message()}",
                    exc_info=is_exc_info,
                )
            else:
                # Return INTERNAL_SERVER_ERROR(500) if it is not a APIErrorResponse
                response_status_codes_counter.labels(
                    request.url.path, InferenceStatusCodes.INTERNAL_SERVER_ERROR.value
                ).inc()

                user_id = util.get_state(request, RequestStateKey.USER_ID)
                if user_id:
                    analytics.track_event(
                        user_id,
                        AnalyticsEvent(
                            EventName.API_RESPONSE,
                            {
                                "request_id": request_id,
                                "status_code": InferenceStatusCodes.INTERNAL_SERVER_ERROR,
                            },
                        ),
                    )
                logger.error(
                    f"Error while handling request. request_id={request_id} "
                    f"request_path={request.url.path} ",
                    exc_info=True,
                )
            raise error from None


# pylint: disable=C2801
def _set_state(request: Request, state_key: RequestStateKey, value: Any):
    request.state.__setattr__(state_key.value, value)


def _get_state(request: Request, state_key: RequestStateKey) -> Optional[Any]:
    return getattr(request.state, state_key.value, None)
