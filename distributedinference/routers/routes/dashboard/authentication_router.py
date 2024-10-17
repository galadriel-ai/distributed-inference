from fastapi import APIRouter
from fastapi import Depends

import settings
from distributedinference import api_logger
from distributedinference import dependencies
from distributedinference.analytics.analytics import Analytics
from distributedinference.domain.user.entities import User
from distributedinference.repository.authentication_api_repository import (
    AuthenticationApiRepository,
)
from distributedinference.repository.user_repository import UserRepository
from distributedinference.service.auth import authentication
from distributedinference.service.auth import login_service
from distributedinference.service.auth import reset_username_and_password_service
from distributedinference.service.auth import set_user_profile_data_service
from distributedinference.service.auth import signup_service
from distributedinference.service.auth import validate_email_service
from distributedinference.service.auth.entities import LoginRequest
from distributedinference.service.auth.entities import LoginResponse
from distributedinference.service.auth.entities import ResetUserPasswordRequest
from distributedinference.service.auth.entities import ResetUserPasswordResponse
from distributedinference.service.auth.entities import SetUserProfileDataRequest
from distributedinference.service.auth.entities import SetUserProfileDataResponse
from distributedinference.service.auth.entities import SignupRequest
from distributedinference.service.auth.entities import SignupResponse
from distributedinference.service.auth.entities import ValidateEmailRequest
from distributedinference.service.auth.entities import ValidateEmailResponse

TAG = "Authentication"
router = APIRouter(prefix="/auth")
router.tags = [TAG]

logger = api_logger.get()


@router.post(
    "/signup",
    summary="Sign up new user",
    description="Sign up new user with email, username and password",
    response_description="Returns a session token, or a helpful error.",
    response_model=SignupResponse,
    include_in_schema=not settings.is_production(),
)
async def signup(
    request: SignupRequest,
    auth_repository: AuthenticationApiRepository = Depends(
        dependencies.get_authentication_api_repository
    ),
    user_repository: UserRepository = Depends(dependencies.get_user_repository),
    analytics: Analytics = Depends(dependencies.get_analytics),
):
    return await signup_service.execute(
        request, auth_repository, user_repository, analytics
    )


@router.post(
    "/validate-email",
    summary="Validate user email.",
    description="Validate user email.",
    response_description="Returns status.",
    response_model=ValidateEmailResponse,
    include_in_schema=not settings.is_production(),
)
async def validate_email(
    request: ValidateEmailRequest,
    auth_repository: AuthenticationApiRepository = Depends(
        dependencies.get_authentication_api_repository
    ),
    user_repository: UserRepository = Depends(dependencies.get_user_repository),
):
    return await validate_email_service.execute(
        request, auth_repository, user_repository
    )


@router.post(
    "/reset_user_password",
    summary="Validate magic link and reset user password",
    description="Validate magic link, after using the /signup endpoint and save user password.",
    response_description="Returns a session token, or a helpful error.",
    response_model=ResetUserPasswordResponse,
    include_in_schema=not settings.is_production(),
)
async def reset_user_password(
    request: ResetUserPasswordRequest,
    auth_repository: AuthenticationApiRepository = Depends(
        dependencies.get_authentication_api_repository
    ),
    user_repository: UserRepository = Depends(dependencies.get_user_repository),
    analytics: Analytics = Depends(dependencies.get_analytics),
):
    return await reset_username_and_password_service.execute(
        request, auth_repository, user_repository, analytics
    )


@router.post(
    "/login",
    summary="Log in with password",
    description="Validate password and log in.",
    response_description="Returns a session token, or a helpful error.",
    response_model=LoginResponse,
    include_in_schema=not settings.is_production(),
)
async def login(
    request: LoginRequest,
    auth_repository: AuthenticationApiRepository = Depends(
        dependencies.get_authentication_api_repository
    ),
    user_repository: UserRepository = Depends(dependencies.get_user_repository),
    analytics: Analytics = Depends(dependencies.get_analytics),
):
    return await login_service.execute(
        request, auth_repository, user_repository, analytics
    )


@router.post(
    "/profile",
    summary="Save profile",
    description="Save user profile.",
    response_description="",
    response_model=SetUserProfileDataResponse,
    include_in_schema=not settings.is_production(),
)
async def profile_data(
    request: SetUserProfileDataRequest,
    user: User = Depends(authentication.validate_session_token),
    user_repository: UserRepository = Depends(dependencies.get_user_repository),
    analytics: Analytics = Depends(dependencies.get_analytics),
):
    return await set_user_profile_data_service.execute(
        request, user, user_repository, analytics
    )
