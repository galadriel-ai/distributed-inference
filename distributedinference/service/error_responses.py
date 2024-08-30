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


class InferenceError(APIErrorResponse):
    def __init__(self, status_code, message_extra: str = None):
        self.status_code = status_code
        self.message_extra = message_extra

    def to_status_code(self) -> status:
        return self.status_code

    def to_code(self) -> str:
        return "inference_error"

    def to_message(self) -> str:
        result = "Inference error"
        if self.message_extra:
            result += f" - {self.message_extra}"
        return result


class AuthorizationMissingAPIError(APIErrorResponse):
    def __init__(self):
        pass

    def to_status_code(self) -> status:
        return status.HTTP_401_UNAUTHORIZED

    def to_code(self) -> str:
        return "authorization_missing"

    def to_message(self) -> str:
        return f"Request is missing or has invalid 'Authorization' header."


class InvalidCredentialsAPIError(APIErrorResponse):
    def __init__(self, message_extra: str = None):
        self.message_extra = message_extra

    def to_status_code(self) -> status:
        return status.HTTP_401_UNAUTHORIZED

    def to_code(self) -> str:
        return "invalid_credentials"

    def to_message(self) -> str:
        result = "Invalid credentials"
        if self.message_extra:
            result += f" - {self.message_extra}"
        return result


class NotFoundAPIError(APIErrorResponse):
    def __init__(self, message_extra: str = None):
        self.message_extra = message_extra

    def to_status_code(self) -> status:
        return status.HTTP_404_NOT_FOUND

    def to_code(self) -> str:
        return "not_found"

    def to_message(self) -> str:
        return "Can't find the requested resource"


class ValidationError(APIErrorResponse):
    """Raised when a validation error occurs"""

    def __init__(self):
        pass

    def to_status_code(self) -> status:
        return status.HTTP_422_UNPROCESSABLE_ENTITY

    def to_code(self) -> str:
        return "unprocessable_entity"

    def to_message(self) -> str:
        return "Can't process the data."


class InternalServerAPIError(APIErrorResponse):
    """Raised when an internal server error occurs"""

    def __init__(self):
        pass

    def to_status_code(self) -> status:
        return status.HTTP_500_INTERNAL_SERVER_ERROR

    def to_code(self) -> str:
        return "internal_server_error"

    def to_message(self) -> str:
        return "The request could not be completed due to an internal server error."


class NoAvailableInferenceNodesError(APIErrorResponse):
    def __init__(self):
        pass

    def to_status_code(self) -> status:
        return status.HTTP_503_SERVICE_UNAVAILABLE

    def to_code(self) -> str:
        return "no_available_inference_nodes"

    def to_message(self) -> str:
        return "No available inference nodes to process the request."
