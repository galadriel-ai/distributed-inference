from fastapi import APIRouter
from fastapi import Depends

from distributedinference import api_logger
from distributedinference import dependencies
from distributedinference.domain.user.entities import User
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.auth import authentication
from distributedinference.service.network import get_network_stats_service
from distributedinference.service.network.entities import NetworkStatsResponse

TAG = "Network"
router = APIRouter(prefix="/network")
router.tags = [TAG]

logger = api_logger.get()


@router.get(
    "/stats",
    name="Node Stats",
    response_model=NetworkStatsResponse,
)
async def node_stats(
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    _: User = Depends(authentication.validate_api_key_header),
):
    return await get_network_stats_service.execute(node_repository)
