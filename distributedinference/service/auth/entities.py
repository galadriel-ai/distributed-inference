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
    username: str = Field(description="User name")
    password: str = Field(description="User password")


class SetUserPasswordResponse(ApiResponse):
    session_token: str = Field(description="Session token")


class LoginRequest(BaseModel):
    username: str = Field(description="Username")
    password: str = Field(description="User password")


class LoginResponse(ApiResponse):
    session_token: str = Field(description="Session token")
    onboarding_completed: bool = Field(description="Onboarding status")
    email: str = Field("User email address")


class SetUserProfileDataRequest(BaseModel):
    data: dict = Field(description="User profile data")


class SetUserProfileDataResponse(ApiResponse):
    pass
