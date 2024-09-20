from fastapi import APIRouter
from fastapi import Depends

import settings
from distributedinference import api_logger
from distributedinference import dependencies
from distributedinference.analytics.analytics import Analytics
from distributedinference.analytics.analytics import AnalyticsEvent
from distributedinference.analytics.analytics import EventName
from distributedinference.domain.user.entities import User
from distributedinference.repository.metrics_queue_repository import (
    MetricsQueueRepository,
)
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.repository.user_repository import UserRepository
from distributedinference.service.api_key import create_api_key_service
from distributedinference.service.api_key import get_api_keys_service
from distributedinference.service.auth import authentication
from distributedinference.service.completions import chat_completions_handler_service
from distributedinference.service.completions.entities import ChatCompletion
from distributedinference.service.completions.entities import ChatCompletionRequest
from distributedinference.service.network import get_network_stats_service
from distributedinference.service.network.entities import CreateApiKeyResponse
from distributedinference.service.network.entities import GetApiKeysResponse
from distributedinference.service.network.entities import NetworkStatsResponse
from distributedinference.service.node import create_node_service
from distributedinference.service.node import get_user_aggregated_stats_service
from distributedinference.service.node import get_user_nodes_service
from distributedinference.service.node.entities import CreateNodeRequest
from distributedinference.service.node.entities import CreateNodeResponse
from distributedinference.service.node.entities import GetUserAggregatedStatsResponse
from distributedinference.service.node.entities import ListNodeResponse

TAG = "Dashboard Network"
router = APIRouter(prefix="/dashboard")
router.tags = [TAG]

logger = api_logger.get()


@router.get(
    "/user-node-stats",
    name="Node Stats",
    response_model=GetUserAggregatedStatsResponse,
    include_in_schema=not settings.is_production(),
)
async def get_node_stats(
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    tokens_repository: TokensRepository = Depends(dependencies.get_tokens_repository),
    user: User = Depends(authentication.validate_session_token),
):
    return await get_user_aggregated_stats_service.execute(
        user, node_repository, tokens_repository
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
    analytics=Depends(dependencies.get_analytics),
):
    analytics.track_event(user.uid, AnalyticsEvent(EventName.CREATE_API_KEY, {}))
    return await create_api_key_service.execute(user, user_repository)


@router.post("/node", name="Create Node", response_model=CreateNodeResponse)
async def create_node(
    request: CreateNodeRequest,
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    user: User = Depends(authentication.validate_session_token),
    analytics=Depends(dependencies.get_analytics),
):
    analytics.track_event(
        user.uid,
        AnalyticsEvent(EventName.CREATE_NODE, {"node_name": request.node_name}),
    )
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


@router.post(
    "/chat/completions",
    summary="Creates a model response for the given chat conversation.",
    description="Given a list of messages comprising a conversation, the model will return a response.",
    response_description="Returns a chat completion object, or a streamed sequence of chat completion chunk objects if the request is streamed.",
    response_model=ChatCompletion,
)
# pylint: disable=too-many-arguments
async def completions(
    request: ChatCompletionRequest,
    user: User = Depends(authentication.validate_session_token),
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    tokens_repository: TokensRepository = Depends(dependencies.get_tokens_repository),
    metrics_queue_repository: MetricsQueueRepository = Depends(
        dependencies.get_metrics_queue_repository
    ),
    analytics: Analytics = Depends(dependencies.get_analytics),
):
    analytics.track_event(
        user.uid, AnalyticsEvent(EventName.DASHBOARD_CHAT_COMPLETIONS, {})
    )
    # Force streaming
    request.stream = True
    return await chat_completions_handler_service.execute(
        request, user, node_repository, tokens_repository, metrics_queue_repository
    )
