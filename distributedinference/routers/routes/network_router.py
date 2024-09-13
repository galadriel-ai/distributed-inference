from fastapi import APIRouter
from fastapi import Depends

from distributedinference import api_logger
from distributedinference import dependencies
from distributedinference.domain.user.entities import User
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.service.auth import authentication
from distributedinference.service.network import get_network_stats_service
from distributedinference.service.network.entities import NetworkStatsResponse

TAG = "Network"
router = APIRouter(prefix="/network")
router.tags = [TAG]

logger = api_logger.get()


@router.get(
    "/stats",
    name="Network Stats",
    response_model=NetworkStatsResponse,
)
async def network_stats(
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    tokens_repository: TokensRepository = Depends(dependencies.get_tokens_repository),
    _: User = Depends(authentication.validate_api_key_header),
):
    return await get_network_stats_service.execute(node_repository, tokens_repository)
