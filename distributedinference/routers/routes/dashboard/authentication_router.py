from fastapi import APIRouter
from fastapi import Depends

import settings
from distributedinference import api_logger
from distributedinference import dependencies
from distributedinference.repository.authentication_api_repository import (
    AuthenticationApiRepository,
)
from distributedinference.repository.user_repository import UserRepository
from distributedinference.domain.user.entities import User
from distributedinference.service.auth import login_service
from distributedinference.service.auth import set_username_and_password_service
from distributedinference.service.auth import signup_service
from distributedinference.service.auth import authentication
from distributedinference.service.auth import set_user_profile_data_service
from distributedinference.service.auth.entities import LoginRequest
from distributedinference.service.auth.entities import SetUserPasswordRequest
from distributedinference.service.auth.entities import SetUserPasswordResponse
from distributedinference.service.auth.entities import SignupRequest
from distributedinference.service.auth.entities import SignupResponse
from distributedinference.service.auth.entities import SetUserProfileDataRequest
from distributedinference.service.auth.entities import SetUserProfileDataResponse

TAG = "Authentication"
router = APIRouter(prefix="/auth")
router.tags = [TAG]

logger = api_logger.get()


@router.post(
    "/signup",
    summary="Sign up user.",
    description="Sign up a new user.",
    response_description="Returns an email_id, that is required to validate the OTP received by email.",
    response_model=SignupResponse,
    include_in_schema=not settings.is_production(),
)
async def signup(
    request: SignupRequest,
    auth_repository: AuthenticationApiRepository = Depends(
        dependencies.get_authentication_api_repository
    ),
    user_repository: UserRepository = Depends(dependencies.get_user_repository),
):
    return await signup_service.execute(request, auth_repository, user_repository)


@router.post(
    "/set_user_password",
    summary="Validate magic link and set user password",
    description="Validate magic link, after using the /signup endpoint and save user password.",
    response_description="Returns a session token, or a helpful error.",
    response_model=SetUserPasswordResponse,
    include_in_schema=not settings.is_production(),
)
async def set_user_password(
    request: SetUserPasswordRequest,
    auth_repository: AuthenticationApiRepository = Depends(
        dependencies.get_authentication_api_repository
    ),
    user_repository: UserRepository = Depends(dependencies.get_user_repository),
):
    return await set_username_and_password_service.execute(
        request, auth_repository, user_repository
    )


@router.post(
    "/login",
    summary="Log in with password",
    description="Validate password and log in.",
    response_description="Returns a session token, or a helpful error.",
    response_model=SetUserPasswordResponse,
    include_in_schema=not settings.is_production(),
)
async def login(
    request: LoginRequest,
    auth_repository: AuthenticationApiRepository = Depends(
        dependencies.get_authentication_api_repository
    ),
    user_repository: UserRepository = Depends(dependencies.get_user_repository),
):
    return await login_service.execute(request, auth_repository, user_repository)


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
):
    return await set_user_profile_data_service.execute(request, user, user_repository)
