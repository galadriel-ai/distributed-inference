from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import WebSocket
from fastapi.exceptions import WebSocketRequestValidationError

from distributedinference import api_logger
from distributedinference import dependencies
from distributedinference.domain.user.entities import User
from distributedinference.repository.metrics_queue_repository import (
    MetricsQueueRepository,
)
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.repository.user_repository import UserRepository
from distributedinference.service.auth import authentication
from distributedinference.service.node import get_node_benchmark_service
from distributedinference.service.node import get_node_info_service
from distributedinference.service.node import get_node_stats_service
from distributedinference.service.node import save_node_benchmark_service
from distributedinference.service.node import save_node_info_service
from distributedinference.service.node import websocket_service
from distributedinference.service.node.entities import GetNodeBenchmarkResponse
from distributedinference.service.node.entities import GetNodeInfoResponse
from distributedinference.service.node.entities import GetNodeStatsResponse
from distributedinference.service.node.entities import PostNodeBenchmarkRequest
from distributedinference.service.node.entities import PostNodeBenchmarkResponse
from distributedinference.service.node.entities import PostNodeInfoRequest
from distributedinference.service.node.entities import PostNodeInfoResponse

TAG = "Node"
router = APIRouter(prefix="/node")
router.tags = [TAG]

logger = api_logger.get()


@router.websocket(
    "/ws",
    name="Node WebSocket",
)
async def websocket_endpoint(
    websocket: WebSocket,
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    user_repository: UserRepository = Depends(dependencies.get_user_repository),
    metrics_queue_repository: MetricsQueueRepository = Depends(
        dependencies.get_metrics_queue_repository
    ),
):
    user = await authentication.validate_api_key(
        websocket.headers.get("Authorization"),
        user_repository,
    )
    if not user:
        raise WebSocketRequestValidationError("Authorization header is required")

    await websocket_service.execute(
        websocket,
        user,
        websocket.headers.get("Model"),
        node_repository,
        metrics_queue_repository,
    )


@router.get(
    "/info",
    name="Node Info",
    response_model=GetNodeInfoResponse,
)
async def node_info(
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    user: User = Depends(authentication.validate_api_key_header),
):
    return await get_node_info_service.execute(user, node_repository)


@router.get(
    "/stats",
    name="Node Stats",
    response_model=GetNodeStatsResponse,
)
async def node_stats(
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    tokens_repository: TokensRepository = Depends(dependencies.get_tokens_repository),
    user: User = Depends(authentication.validate_api_key_header),
):
    return await get_node_stats_service.execute(
        user, node_repository, tokens_repository
    )


@router.post(
    "/info",
    name="Node Info",
    response_model=PostNodeInfoResponse,
)
async def node_info(
    request: PostNodeInfoRequest,
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    user: User = Depends(authentication.validate_api_key_header),
):
    return await save_node_info_service.execute(request, user.uid, node_repository)


@router.get(
    "/benchmark",
    name="Node Benchmark",
    response_model=GetNodeBenchmarkResponse,
)
async def node_info(
    model: str = Query(..., description="Model name"),
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    user: User = Depends(authentication.validate_api_key_header),
):
    return await get_node_benchmark_service.execute(user, model, node_repository)


@router.post(
    "/benchmark",
    name="Node Benchmark",
    response_model=PostNodeBenchmarkResponse,
)
async def node_info(
    request: PostNodeBenchmarkRequest,
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    user: User = Depends(authentication.validate_api_key_header),
):
    return await save_node_benchmark_service.execute(request, user.uid, node_repository)
