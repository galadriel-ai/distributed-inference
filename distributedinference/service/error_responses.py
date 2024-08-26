from starlette import status


class APIErrorResponse(Exception):
    """Base class for other exceptions"""

    def __init__(self):
        pass

    def to_status_code(self) -> status:
        raise NotImplementedError

    def to_code(self) -> str:
        raise NotImplementedError

    def to_message(self) -> str:
        raise NotImplementedError


class InternalServerAPIError(APIErrorResponse):
    """Raised when an internal server error occurs"""

    def __init__(self):
        pass

    def to_status_code(self) -> status:
        return status.HTTP_500_INTERNAL_SERVER_ERROR

    def to_code(self) -> str:
        return "internal_server_error"

    def to_message(self) -> str:
        return "The request could not be completed due to an " "internal server error."
