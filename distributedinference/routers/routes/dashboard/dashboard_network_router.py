from fastapi import APIRouter
from fastapi import Depends

import settings
from distributedinference import api_logger
from distributedinference import dependencies
from distributedinference.domain.user.entities import User
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.auth import authentication
from distributedinference.service.network import get_network_stats_service
from distributedinference.service.network.entities import NetworkStatsResponse

TAG = "Dashboard Network"
router = APIRouter(prefix="/dashboard-network")
router.tags = [TAG]

logger = api_logger.get()


@router.get(
    "/stats",
    name="Node Stats",
    response_model=NetworkStatsResponse,
    include_in_schema=not settings.is_production(),
)
async def node_stats(
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    _: User = Depends(authentication.validate_session_token),
):
    return await get_network_stats_service.execute(node_repository)
