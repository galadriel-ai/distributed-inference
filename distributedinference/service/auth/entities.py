from pydantic import BaseModel
from pydantic import Field

from distributedinference.service.entities import ApiResponse


class SignupRequest(BaseModel):
    email: str = Field(description="User email")
    password: str = Field(description="User password")


class SignupResponse(ApiResponse):
    email: str = Field(description="User email")
    user_uid: str = Field("User unique identifier")
    session_token: str = Field(description="Session token")


class ValidateEmailRequest(BaseModel):
    email: str = Field(description="User email")


class ValidateEmailResponse(ApiResponse):
    pass


class ResetUserPasswordRequest(BaseModel):
    token: str = Field(
        description="Token gotten from magic link in email from /signup request"
    )
    password: str = Field(description="User password")


class ResetUserPasswordResponse(SignupResponse):
    pass


class LoginRequest(BaseModel):
    email: str = Field(description="Email")
    password: str = Field(description="User password")


class LoginResponse(ApiResponse):
    session_token: str = Field(description="Session token")
    onboarding_completed: bool = Field(description="Onboarding status")
    user_uid: str = Field("User unique identifier")
    email: str = Field("User email address")


class SetUserProfileDataRequest(BaseModel):
    data: dict = Field(description="User profile data")


class SetUserProfileDataResponse(ApiResponse):
    pass
