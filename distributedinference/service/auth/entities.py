from pydantic import BaseModel
from pydantic import Field

from distributedinference.service.entities import ApiResponse


class SignupRequest(BaseModel):
    email: str = Field(description="User email")


class SignupResponse(ApiResponse):
    pass


class SetUserPasswordRequest(BaseModel):
    token: str = Field(
        description="Token gotten from magic link in email from /signup request"
    )
    password: str = Field(description="User password")


class SetUserPasswordResponse(ApiResponse):
    session_token: str = Field(description="Session token")


class LoginRequest(BaseModel):
    email: str = Field(description="User email")
    password: str = Field(description="User password")


class LoginResponse(ApiResponse):
    session_token: str = Field(description="Session token")
