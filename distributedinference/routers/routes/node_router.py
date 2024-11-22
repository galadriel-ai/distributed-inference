from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import WebSocket
from fastapi import status
from fastapi.exceptions import WebSocketException

from distributedinference import api_logger
from distributedinference import dependencies
from distributedinference.analytics.analytics import (
    AnalyticsEvent,
    EventName,
    Analytics,
)
from distributedinference.domain.user.entities import User
from distributedinference.repository.benchmark_repository import BenchmarkRepository
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.node_stats_repository import NodeStatsRepository
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
from distributedinference.service.node.protocol.protocol_handler import ProtocolHandler

TAG = "Node"
router = APIRouter(prefix="/node")
router.tags = [TAG]

logger = api_logger.get()


@router.websocket(
    "/ws",
    name="Node WebSocket",
)
# pylint: disable=too-many-arguments
async def websocket_endpoint(
    websocket: WebSocket,
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    benchmark_repository: BenchmarkRepository = Depends(
        dependencies.get_benchmark_repository
    ),
    user_repository: UserRepository = Depends(dependencies.get_user_repository),
    analytics: Analytics = Depends(dependencies.get_analytics),
    protocol_handler: ProtocolHandler = Depends(dependencies.get_protocol_handler),
):
    user = await authentication.validate_api_key(
        websocket.headers.get("Authorization"),
        user_repository,
    )

    node_id = websocket.headers.get("Node-Id")
    if not node_id:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Node-Id header is required",
        )
    node_info = await authentication.validate_node_name(user, node_id, node_repository)

    await websocket_service.execute(
        websocket,
        user,
        node_info,
        websocket.headers.get("Model"),
        node_repository,
        benchmark_repository,
        analytics,
        protocol_handler,
    )


@router.get(
    "/info",
    name="Node Info",
    response_model=GetNodeInfoResponse,
)
async def get_info(
    node_id: str = Query(..., description="Node id"),
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    analytics: Analytics = Depends(dependencies.get_analytics),
    user: User = Depends(authentication.validate_api_key_header),
):
    node_info = await authentication.validate_node_name_basic(
        user, node_id, node_repository
    )
    analytics.track_event(
        user.uid, AnalyticsEvent(EventName.GET_NODE_INFO, {"node_id": node_id})
    )
    return await get_node_info_service.execute(node_info, node_repository)


@router.get(
    "/stats",
    name="Node Stats",
    response_model=GetNodeStatsResponse,
)
# pylint: disable=too-many-arguments, R0913
async def get_stats(
    node_id: str = Query(..., description="Node id"),
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    node_stats_repository: NodeStatsRepository = Depends(
        dependencies.get_node_stats_repository
    ),
    tokens_repository: TokensRepository = Depends(dependencies.get_tokens_repository),
    analytics: Analytics = Depends(dependencies.get_analytics),
    user: User = Depends(authentication.validate_api_key_header),
):
    node_info = await authentication.validate_node_name_basic(
        user, node_id, node_repository
    )
    analytics.track_event(
        user.uid, AnalyticsEvent(EventName.GET_NODE_STATS, {"node_id": node_id})
    )
    return await get_node_stats_service.execute(
        user, node_info, node_stats_repository, tokens_repository
    )


@router.post(
    "/info",
    name="Node Info",
    response_model=PostNodeInfoResponse,
)
async def post_info(
    request: PostNodeInfoRequest,
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    analytics: Analytics = Depends(dependencies.get_analytics),
    user: User = Depends(authentication.validate_api_key_header),
):
    node_info = await authentication.validate_node_name_basic(
        user, request.node_id, node_repository
    )
    analytics.track_event(
        user.uid,
        AnalyticsEvent(
            EventName.POST_NODE_INFO,
            {"node_id": node_info.node_id},
        ),
    )
    return await save_node_info_service.execute(
        request, node_info, user.uid, node_repository
    )


@router.get(
    "/benchmark",
    name="Node Benchmark",
    response_model=GetNodeBenchmarkResponse,
)
# pylint: disable=too-many-arguments, R0913
async def get_benchmark(
    node_id: str = Query(..., description="Node id"),
    model: str = Query(..., description="Model name"),
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    benchmark_repository: BenchmarkRepository = Depends(
        dependencies.get_benchmark_repository
    ),
    analytics: Analytics = Depends(dependencies.get_analytics),
    user: User = Depends(authentication.validate_api_key_header),
):
    node_info = await authentication.validate_node_name_basic(
        user, node_id, node_repository
    )
    analytics.track_event(
        user.uid, AnalyticsEvent(EventName.GET_NODE_BENCHMARK, {"node_id": node_id})
    )
    return await get_node_benchmark_service.execute(
        user, node_info, model, benchmark_repository
    )


@router.post(
    "/benchmark",
    name="Node Benchmark",
    response_model=PostNodeBenchmarkResponse,
)
async def post_benchmark(
    request: PostNodeBenchmarkRequest,
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    benchmark_repository: BenchmarkRepository = Depends(
        dependencies.get_benchmark_repository
    ),
    analytics: Analytics = Depends(dependencies.get_analytics),
    user: User = Depends(authentication.validate_api_key_header),
):
    node_info = await authentication.validate_node_name(
        user, request.node_id, node_repository
    )
    analytics.track_event(
        user.uid,
        AnalyticsEvent(EventName.POST_NODE_BENCHMARK, {"node_id": node_info.node_id}),
    )
    return await save_node_benchmark_service.execute(
        request, node_info, user.uid, benchmark_repository
    )
