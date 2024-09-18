from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query

import settings
from distributedinference import api_logger
from distributedinference import dependencies
from distributedinference.domain.user.entities import User
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.repository.user_repository import UserRepository
from distributedinference.service.api_key import create_api_key_service
from distributedinference.service.api_key import get_api_keys_service
from distributedinference.service.auth import authentication
from distributedinference.service.network import get_network_stats_service
from distributedinference.service.network.entities import CreateApiKeyResponse
from distributedinference.service.network.entities import GetApiKeysResponse
from distributedinference.service.network.entities import NetworkStatsResponse
from distributedinference.service.node import create_node_service
from distributedinference.service.node import get_node_stats_service
from distributedinference.service.node import get_user_nodes_service
from distributedinference.service.node.entities import CreateNodeRequest
from distributedinference.service.node.entities import CreateNodeResponse
from distributedinference.service.node.entities import GetNodeStatsResponse
from distributedinference.service.node.entities import ListNodeResponse

TAG = "Dashboard Network"
router = APIRouter(prefix="/dashboard")
router.tags = [TAG]

logger = api_logger.get()


@router.get(
    "/node-stats",
    name="Node Stats",
    response_model=GetNodeStatsResponse,
    include_in_schema=not settings.is_production(),
)
async def get_node_stats(
    node_id: str = Query(..., description="Node id"),
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    tokens_repository: TokensRepository = Depends(dependencies.get_tokens_repository),
    user: User = Depends(authentication.validate_session_token),
):
    node_info = await authentication.validate_node_name(user, node_id, node_repository)
    return await get_node_stats_service.execute(
        user, node_info, node_repository, tokens_repository
    )


@router.get(
    "/network-stats",
    name="Network Stats",
    response_model=NetworkStatsResponse,
    include_in_schema=not settings.is_production(),
)
async def get_network_stats(
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    tokens_repository: TokensRepository = Depends(dependencies.get_tokens_repository),
    _: User = Depends(authentication.validate_session_token),
):
    return await get_network_stats_service.execute(node_repository, tokens_repository)


@router.get(
    "/api-key",
    name="Api key",
    response_model=GetApiKeysResponse,
    include_in_schema=not settings.is_production(),
)
async def get_api_key(
    user_repository: UserRepository = Depends(dependencies.get_user_repository),
    user: User = Depends(authentication.validate_session_token),
):
    return await get_api_keys_service.execute(user, user_repository)


@router.post(
    "/api-key",
    name="Api key",
    response_model=CreateApiKeyResponse,
    include_in_schema=not settings.is_production(),
)
async def post_api_key(
    user_repository: UserRepository = Depends(dependencies.get_user_repository),
    user: User = Depends(authentication.validate_session_token),
):
    return await create_api_key_service.execute(user, user_repository)


@router.post("/node", name="Create Node", response_model=CreateNodeResponse)
async def create_node(
    request: CreateNodeRequest,
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    user: User = Depends(authentication.validate_session_token),
):
    return await create_node_service.execute(request, user.uid, node_repository)


@router.get("/nodes", name="List all nodes", response_model=ListNodeResponse)
async def list_nodes(
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    tokens_repository: TokensRepository = Depends(dependencies.get_tokens_repository),
    user: User = Depends(authentication.validate_session_token),
):
    return await get_user_nodes_service.execute(
        user.uid, node_repository, tokens_repository
    )
