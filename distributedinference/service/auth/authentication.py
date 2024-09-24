from typing import Optional

from fastapi import Depends
from fastapi import Security
from fastapi.security import APIKeyHeader
from fastapi import Request

from distributedinference import api_logger
from distributedinference.dependencies import get_authentication_api_repository
from distributedinference.dependencies import get_user_repository
from distributedinference.domain.node.entities import NodeInfo
from distributedinference.domain.user.entities import User
from distributedinference.repository.authentication_api_repository import (
    AuthenticationApiRepository,
)
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.user_repository import UserRepository
from distributedinference.service import error_responses
from distributedinference.service.middleware import util
from distributedinference.service.middleware.entitites import RequestStateKey

API_KEY_NAME = "Authorization"
API_KEY_HEADER = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

logger = api_logger.get()


async def validate_api_key_header(
    request: Request,
    api_key_header: str = Security(API_KEY_HEADER),
    user_repository: UserRepository = Depends(get_user_repository),
) -> Optional[User]:
    return await validate_api_key(request, api_key_header, user_repository)


async def validate_api_key(
    request: Optional[Request],
    api_key_header: Optional[str],
    user_repository: UserRepository,
) -> Optional[User]:
    if not api_key_header:
        raise error_responses.AuthorizationMissingAPIError()

    if not api_key_header.startswith("Bearer "):
        raise error_responses.InvalidCredentialsAPIError(
            message_extra="Authorization header needs to start with 'Bearer '"
        )

    api_key_header = api_key_header.replace("Bearer ", "")
    user = await user_repository.get_user_by_api_key(api_key_header)
    if user:
        if request:
            util.set_state(request, RequestStateKey.USER_ID, user.uid)
        return user
    raise error_responses.InvalidCredentialsAPIError(message_extra="API Key not found.")


async def validate_session_token(
    session_token_header: str = Security(API_KEY_HEADER),
    auth_repository: AuthenticationApiRepository = Depends(
        get_authentication_api_repository
    ),
    user_repository: UserRepository = Depends(get_user_repository),
) -> Optional[User]:
    if not session_token_header.startswith("Bearer "):
        raise error_responses.InvalidCredentialsAPIError(
            message_extra="Authorization header needs to start with 'Bearer '"
        )

    formatted_session_token_header = session_token_header.replace("Bearer ", "")

    authenticated_user = await auth_repository.authenticate_session(
        formatted_session_token_header
    )
    user = await user_repository.get_user_by_authentication_id(
        authenticated_user.provider_user_id
    )
    if user:
        return user
    raise error_responses.InvalidCredentialsAPIError(message_extra="User not found.")


async def validate_node_name(
    user: User,
    node_name: Optional[str],
    node_repository: NodeRepository,
) -> Optional[NodeInfo]:
    if not node_name:
        raise error_responses.NotFoundAPIError(message_extra="Node ID not provided")
    node_info = await node_repository.get_node_info_by_name(user.uid, node_name)
    if not node_info:
        raise error_responses.NotFoundAPIError(
            message_extra="Node with the given name not found."
        )
    return node_info
