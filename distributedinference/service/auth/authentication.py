from typing import Optional

from fastapi import Depends
from fastapi import Security
from fastapi.security import APIKeyHeader
from fastapi import Request

from distributedinference import api_logger
from distributedinference.dependencies import get_authentication_api_repository
from distributedinference.dependencies import get_user_repository
from distributedinference.domain.node.entities import FullNodeInfo
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
API_KEY_HEADER = APIKeyHeader(
    name=API_KEY_NAME,
    auto_error=False,
    description="Bearer authentication header.\n\n"
    "example value: `Bearer Galadriel-API-key`\n\n"
    "Get API key from [Galadriel dashboard](https://dashboard.galadriel.com).",
)

FORWARDING_NAME = "Peer-Forwarding-From"
FORWARDING_HEADER = APIKeyHeader(name=FORWARDING_NAME, auto_error=False)

logger = api_logger.get()


async def get_forwarding_origin(
    forwarding_origin_header: str = Security(FORWARDING_HEADER),
) -> Optional[str]:
    return forwarding_origin_header or None


async def validate_api_key_header(
    request: Request,
    api_key_header: str = Security(API_KEY_HEADER),
    user_repository: UserRepository = Depends(get_user_repository),
) -> User:
    user = await validate_api_key(api_key_header, user_repository)
    util.set_state(request, RequestStateKey.USER_ID, user.uid)
    return user


async def validate_api_key(
    api_key_header: Optional[str],
    user_repository: UserRepository,
) -> User:
    if not api_key_header:
        raise error_responses.AuthorizationMissingAPIError()

    if not api_key_header.startswith("Bearer "):
        raise error_responses.InvalidCredentialsAPIError(
            message_extra="Authorization header needs to start with 'Bearer '"
        )

    api_key_header = api_key_header.replace("Bearer ", "")
    user = await user_repository.get_user_by_api_key(api_key_header)
    if not user:
        raise error_responses.InvalidCredentialsAPIError(
            message_extra="API Key not found."
        )
    return user


async def validate_session_token(
    request: Request,
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

    try:
        authenticated_user = await auth_repository.authenticate_session(
            formatted_session_token_header
        )
    except Exception:
        raise error_responses.InvalidCredentialsAPIError("Invalid session_token")
    user = await user_repository.get_user_by_authentication_id(
        authenticated_user.provider_user_id
    )

    if not user:
        raise error_responses.InvalidCredentialsAPIError(
            message_extra="User not found."
        )

    util.set_state(request, RequestStateKey.USER_ID, user.uid)
    return user


async def validate_node_name_basic(
    user: User,
    node_name: Optional[str],
    node_repository: NodeRepository,
) -> NodeInfo:
    if not node_name:
        raise error_responses.NotFoundAPIError(message_extra="Node ID not provided")
    node_info = await node_repository.get_node_info_by_name(user.uid, node_name)
    if not node_info:
        raise error_responses.NotFoundAPIError(
            message_extra="Node with the given name not found."
        )
    return node_info


async def validate_node_name(
    user: User,
    node_name: Optional[str],
    node_repository: NodeRepository,
) -> FullNodeInfo:
    if not node_name:
        raise error_responses.NotFoundAPIError(message_extra="Node ID not provided")
    node_info = await node_repository.get_full_node_info_by_name(user.uid, node_name)
    if not node_info:
        raise error_responses.NotFoundAPIError(
            message_extra="Node details with the given name not found, "
            "or node hardware has not been reported."
        )
    return node_info
