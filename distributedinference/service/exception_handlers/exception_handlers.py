from fastapi import Request
from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse

from distributedinference.service.error_responses import APIErrorResponse
from distributedinference.service.error_responses import InternalServerAPIError
from distributedinference.utils import http_headers


# pylint: disable=W0613
async def custom_exception_handler(request: Request, error: Exception):
    if not isinstance(error, APIErrorResponse):
        error = InternalServerAPIError()
    headers = {}
    if hasattr(error, "headers"):
        headers = error.headers
    return await http_headers.add_response_headers(
        JSONResponse(
            status_code=error.to_status_code(),
            content=jsonable_encoder(
                {
                    "response": "NOK",
                    "error": {
                        "status_code": error.to_status_code(),
                        "code": error.to_code(),
                        "message": error.to_message(),
                    },
                }
            ),
            headers=headers,
        ),
    )
