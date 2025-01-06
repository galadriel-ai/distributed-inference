from typing import Optional

from starlette import status


class APIErrorResponse(Exception):
    """Base class for other exceptions"""

    def __init__(self):
        pass

    def to_status_code(self) -> int:
        raise NotImplementedError

    def to_code(self) -> str:
        raise NotImplementedError

    def to_message(self) -> str:
        raise NotImplementedError


class InferenceError(APIErrorResponse):
    def __init__(self, status_code, message_extra: Optional[str] = None):
        self.status_code = status_code
        self.message_extra = message_extra

    def to_status_code(self) -> int:
        return self.status_code

    def to_code(self) -> str:
        return "inference_error"

    def to_message(self) -> str:
        result = "Inference error"
        if self.message_extra:
            result += f" - {self.message_extra}"
        return result


class EmbeddingError(APIErrorResponse):
    def __init__(self, status_code: int, message_extra: Optional[str] = None):
        self.status_code = status_code
        self.message_extra = message_extra

    def to_status_code(self) -> int:
        return self.status_code

    def to_code(self) -> str:
        return "embedding_error"

    def to_message(self) -> str:
        result = "Embedding error"
        if self.message_extra:
            result += f" - {self.message_extra}"
        return result


class AuthorizationProviderAPIError(APIErrorResponse):
    """
    Wrapper for our authorization provider errors
    User is expected to take some action to resolve these
    e.g. reset their password
    """

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message

    def to_status_code(self) -> int:
        return status.HTTP_400_BAD_REQUEST

    def to_code(self) -> str:
        return self.code

    def to_message(self) -> str:
        return self.message


class AuthorizationMissingAPIError(APIErrorResponse):
    def __init__(self):
        pass

    def to_status_code(self) -> int:
        return status.HTTP_401_UNAUTHORIZED

    def to_code(self) -> str:
        return "authorization_missing"

    def to_message(self) -> str:
        return "Request is missing or has invalid 'Authorization' header."


class InvalidCredentialsAPIError(APIErrorResponse):
    def __init__(self, message_extra: Optional[str] = None):
        self.message_extra = message_extra

    def to_status_code(self) -> int:
        return status.HTTP_401_UNAUTHORIZED

    def to_code(self) -> str:
        return "invalid_credentials"

    def to_message(self) -> str:
        result = "Invalid credentials"
        if self.message_extra:
            result += f" - {self.message_extra}"
        return result


class InvalidRequestParameterError(APIErrorResponse):
    def __init__(self, message: str):
        self.message = message

    def to_status_code(self) -> int:
        return status.HTTP_400_BAD_REQUEST

    def to_code(self) -> str:
        return "invalid_request_parameter"

    def to_message(self) -> str:
        return self.message


class NotFoundAPIError(APIErrorResponse):
    def __init__(self, message_extra: Optional[str] = None):
        self.message_extra = message_extra

    def to_status_code(self) -> int:
        return status.HTTP_404_NOT_FOUND

    def to_code(self) -> str:
        return "not_found"

    def to_message(self) -> str:
        return "Can't find the requested resource" + (
            f". {self.message_extra}" if self.message_extra else ""
        )


class UsernameAlreadyExistsAPIError(APIErrorResponse):
    def __init__(self):
        pass

    def to_status_code(self) -> int:
        return status.HTTP_409_CONFLICT

    def to_code(self) -> str:
        return "username_already_exists"

    def to_message(self) -> str:
        return "Username already exists."


class ValidationError(APIErrorResponse):
    """Raised when a validation error occurs"""

    def __init__(self):
        pass

    def to_status_code(self) -> int:
        return status.HTTP_422_UNPROCESSABLE_ENTITY

    def to_code(self) -> str:
        return "unprocessable_entity"

    def to_message(self) -> str:
        return "Can't process the data."


class ValidationTypeError(APIErrorResponse):
    def __init__(self, message: str):
        self.message = message

    def to_status_code(self) -> int:
        return status.HTTP_422_UNPROCESSABLE_ENTITY

    def to_code(self) -> str:
        return "unprocessable_entity"

    def to_message(self) -> str:
        return self.message


class RateLimitError(APIErrorResponse):
    def __init__(self, headers: dict):
        self.headers = headers

    def to_status_code(self) -> int:
        return status.HTTP_429_TOO_MANY_REQUESTS

    def to_code(self) -> str:
        return "rate_limit_exceeded"

    def to_message(self) -> str:
        return "Rate limit exceeded"


class InternalServerAPIError(APIErrorResponse):
    """Raised when an internal server error occurs"""

    def __init__(self):
        pass

    def to_status_code(self) -> int:
        return status.HTTP_500_INTERNAL_SERVER_ERROR

    def to_code(self) -> str:
        return "internal_server_error"

    def to_message(self) -> str:
        return "The request could not be completed due to an internal server error."


class NoAvailableInferenceNodesError(APIErrorResponse):
    def __init__(self):
        pass

    def to_status_code(self) -> int:
        return status.HTTP_503_SERVICE_UNAVAILABLE

    def to_code(self) -> str:
        return "no_available_inference_nodes"

    def to_message(self) -> str:
        return "No available inference nodes to process the request."


class UnsupportedClientError(APIErrorResponse):
    def __init__(self, client_name: str):
        self.client_name = client_name

    def to_status_code(self) -> int:
        return status.HTTP_426_UPGRADE_REQUIRED

    def to_code(self) -> str:
        return "unsupported_client"

    def to_message(self) -> str:
        return f"Unsupported client: {self.client_name}"


class UnsupportedClientVersionError(APIErrorResponse):
    def __init__(self, client_name: str, client_version: str, min_version: str):
        self.client_name = client_name
        self.client_version = client_version
        self.min_version = min_version

    def to_status_code(self) -> int:
        return status.HTTP_426_UPGRADE_REQUIRED

    def to_code(self) -> str:
        return "unsupported_client_version"

    def to_message(self) -> str:
        base_message = f"Unsupported client version {self.client_version} for client {self.client_name}"
        if self.min_version:
            return f"{base_message}. Minimum supported version is {self.min_version}."
        return base_message


class UnsupportedModelError(APIErrorResponse):
    def __init__(self, model_name: str):
        self.model_name = model_name

    def to_status_code(self) -> int:
        return status.HTTP_404_NOT_FOUND

    def to_code(self) -> str:
        return "unsupported_model"

    def to_message(self) -> str:
        return f"Your requested model {self.model_name} is currently not supported."


class UnsupportedRequestParameterError(APIErrorResponse):
    def __init__(self, message: str):
        self.message = message

    def to_status_code(self) -> int:
        return status.HTTP_400_BAD_REQUEST

    def to_code(self) -> str:
        return "unsupported_request_parameter"

    def to_message(self) -> str:
        return f"Unsupported request parameter: {self.message}"
