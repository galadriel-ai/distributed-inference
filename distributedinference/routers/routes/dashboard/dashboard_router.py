from fastapi import APIRouter
from fastapi import Depends

import settings
from distributedinference import api_logger
from distributedinference import dependencies
from distributedinference.domain.user.entities import User
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.service.auth import authentication
from distributedinference.service.network import get_network_stats_service
from distributedinference.service.network.entities import NetworkStatsResponse
from distributedinference.service.node import get_node_stats_service
from distributedinference.service.node.entities import GetNodeStatsResponse

TAG = "Dashboard Network"
router = APIRouter(prefix="/dashboard")
router.tags = [TAG]

logger = api_logger.get()


@router.get(
    "/node_stats",
    name="Node Stats",
    response_model=GetNodeStatsResponse,
    include_in_schema=not settings.is_production(),
)
async def get_node_stats(
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    tokens_repository: TokensRepository = Depends(dependencies.get_tokens_repository),
    user: User = Depends(authentication.validate_session_token),
):
    return await get_node_stats_service.execute(
        user, node_repository, tokens_repository
    )


@router.get(
    "/network_stats",
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
