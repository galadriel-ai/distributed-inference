import typing
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Response

import settings
from distributedinference import api_logger
from distributedinference import dependencies
from distributedinference.analytics.analytics import Analytics
from distributedinference.analytics.analytics import AnalyticsEvent
from distributedinference.analytics.analytics import EventName
from distributedinference.domain.user.entities import User
from distributedinference.repository.billing_repository import BillingRepository
from distributedinference.repository.connected_node_repository import (
    ConnectedNodeRepository,
)
from distributedinference.repository.grafana_api_repository import GrafanaApiRepository
from distributedinference.repository.metrics_queue_repository import (
    MetricsQueueRepository,
)
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.node_stats_repository import NodeStatsRepository
from distributedinference.repository.rate_limit_repository import RateLimitRepository
from distributedinference.repository.tokens_queue_repository import (
    TokensQueueRepository,
)
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.repository.user_node_repository import UserNodeRepository
from distributedinference.repository.user_repository import UserRepository
from distributedinference.service import error_responses
from distributedinference.service.api_key import create_api_key_service
from distributedinference.service.api_key import delete_api_key_service
from distributedinference.service.api_key import get_api_keys_service
from distributedinference.service.api_key import get_example_api_key_service
from distributedinference.service.auth import authentication
from distributedinference.service.completions import chat_completions_handler_service
from distributedinference.service.completions.entities import ChatCompletion
from distributedinference.service.completions.entities import ChatCompletionRequest
from distributedinference.service.graphs import graph_service
from distributedinference.service.graphs.entities import GetGraphResponse
from distributedinference.service.graphs.entities import GetGraphType
from distributedinference.service.network import get_network_stats_service
from distributedinference.service.network.entities import CreateApiKeyResponse
from distributedinference.service.network.entities import DeleteApiKeyRequest
from distributedinference.service.network.entities import DeleteApiKeyResponse
from distributedinference.service.network.entities import GetApiKeysResponse
from distributedinference.service.network.entities import GetUserApiKeyExampleResponse
from distributedinference.service.network.entities import NetworkStatsResponse
from distributedinference.service.node import create_node_service
from distributedinference.service.node import get_user_aggregated_stats_service
from distributedinference.service.node import get_user_nodes_service
from distributedinference.service.node import update_node_service
from distributedinference.service.node.entities import CreateNodeRequest
from distributedinference.service.node.entities import CreateNodeResponse
from distributedinference.service.node.entities import GetUserAggregatedStatsResponse
from distributedinference.service.node.entities import ListNodeResponse
from distributedinference.service.node.entities import UpdateNodeRequest
from distributedinference.service.node.entities import UpdateNodeResponse
from distributedinference.service.rate_limit import rate_limit_service
from distributedinference.service.rate_limit.entities import RateLimitResponse

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
    node_stats_repository: NodeStatsRepository = Depends(
        dependencies.get_node_stats_repository
    ),
    tokens_repository: TokensRepository = Depends(dependencies.get_tokens_repository),
    user: User = Depends(authentication.validate_session_token),
):
    return await get_user_aggregated_stats_service.execute(
        user, node_stats_repository, tokens_repository
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
    "/api-key-example",
    name="Api key example",
    response_model=GetUserApiKeyExampleResponse,
    include_in_schema=not settings.is_production(),
)
async def get_api_key_example(
    user_repository: UserRepository = Depends(dependencies.get_user_repository),
    user: User = Depends(authentication.validate_session_token),
):
    return await get_example_api_key_service.execute(user, user_repository)


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


@router.delete(
    "/api-key",
    name="Api key",
    response_model=DeleteApiKeyResponse,
    include_in_schema=not settings.is_production(),
)
async def delete_api_key(
    request: DeleteApiKeyRequest,
    user_repository: UserRepository = Depends(dependencies.get_user_repository),
    user: User = Depends(authentication.validate_session_token),
    analytics=Depends(dependencies.get_analytics),
):
    analytics.track_event(user.uid, AnalyticsEvent(EventName.DELETE_API_KEY, {}))
    return await delete_api_key_service.execute(request, user, user_repository)


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
    user_node_repository: UserNodeRepository = Depends(
        dependencies.get_user_node_repository
    ),
    user: User = Depends(authentication.validate_session_token),
    analytics=Depends(dependencies.get_analytics),
):
    analytics.track_event(
        user.uid,
        AnalyticsEvent(EventName.CREATE_NODE, {"node_name": request.node_name}),
    )
    return await create_node_service.execute(request, user.uid, user_node_repository)


@router.put("/node", name="Update Node", response_model=UpdateNodeResponse)
async def update_node(
    request: UpdateNodeRequest,
    user_node_repository: UserNodeRepository = Depends(
        dependencies.get_user_node_repository
    ),
    user: User = Depends(authentication.validate_session_token),
    analytics=Depends(dependencies.get_analytics),
):
    node_info = await authentication.validate_node_name_basic(
        user, request.node_id, user_node_repository
    )
    analytics.track_event(
        user.uid,
        AnalyticsEvent(EventName.UPDATE_NODE, {"node_name": request.node_name}),
    )
    return await update_node_service.execute(
        request,
        node_info,
        user_node_repository,
    )


@router.get("/nodes", name="List all nodes", response_model=ListNodeResponse)
async def list_nodes(
    user_node_repository: UserNodeRepository = Depends(
        dependencies.get_user_node_repository
    ),
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    tokens_repository: TokensRepository = Depends(dependencies.get_tokens_repository),
    user: User = Depends(authentication.validate_session_token),
):
    return await get_user_nodes_service.execute(
        user.uid, user_node_repository, node_repository, tokens_repository
    )


@router.post(
    "/chat/completions",
    summary="Creates a model response for the given chat conversation.",
    description="Given a list of messages comprising a conversation, the model will return a response.",
    response_description="Returns a chat completion object, or a streamed sequence of chat completion chunk objects if the request is streamed.",
    response_model=ChatCompletion,
)
# pylint: disable=too-many-arguments, R0801
async def completions(
    request: ChatCompletionRequest,
    response: Response,
    user: User = Depends(authentication.validate_session_token),
    forwarding_from: Optional[str] = Depends(authentication.get_forwarding_origin),
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    connected_node_repository: ConnectedNodeRepository = Depends(
        dependencies.get_connected_node_repository
    ),
    tokens_repository: TokensRepository = Depends(dependencies.get_tokens_repository),
    rate_limit_repository: RateLimitRepository = Depends(
        dependencies.get_rate_limit_repository
    ),
    metrics_queue_repository: MetricsQueueRepository = Depends(
        dependencies.get_metrics_queue_repository
    ),
    tokens_queue_repository: TokensQueueRepository = Depends(
        dependencies.get_tokens_queue_repository
    ),
    user_repository: UserRepository = Depends(dependencies.get_user_repository),
    analytics: Analytics = Depends(dependencies.get_analytics),
):
    analytics.track_event(
        user.uid, AnalyticsEvent(EventName.DASHBOARD_CHAT_COMPLETIONS, {})
    )
    example_api_key = await get_example_api_key_service.execute(user, user_repository)
    if not example_api_key.api_key:
        raise error_responses.InternalServerAPIError()
    updated_user = User(
        uid=user.uid,
        name=user.name,
        email=user.email,
        usage_tier_id=user.usage_tier_id,
        username=user.username,
        profile_data=user.profile_data,
        authentication_id=user.authentication_id,
        currently_using_api_key=example_api_key.api_key,
    )
    # Force streaming
    request.stream = True
    return await chat_completions_handler_service.execute(
        request,
        response,
        updated_user,
        forwarding_from,
        node_repository,
        connected_node_repository,
        tokens_repository,
        rate_limit_repository,
        metrics_queue_repository,
        tokens_queue_repository,
        analytics,
    )


@router.get(
    "/graph",
    name="Get network/node graphs",
    response_model=GetGraphResponse,
    include_in_schema=not settings.is_production(),
)
async def get_graph(
    graph_type: GetGraphType = typing.get_args(GetGraphType)[0],
    user: User = Depends(authentication.validate_session_token),
    node_name: Optional[str] = None,
    grafana_repository: GrafanaApiRepository = Depends(
        dependencies.get_grafana_repository
    ),
    user_node_repository: UserNodeRepository = Depends(
        dependencies.get_user_node_repository
    ),
):
    return await graph_service.execute(
        graph_type, node_name, user, grafana_repository, user_node_repository
    )


@router.get(
    "/rate-limits",
    name="Get current rate limits and usage",
    response_model=RateLimitResponse,
)
async def get_rate_limits(
    user: User = Depends(authentication.validate_session_token),
    tokens_repository: TokensRepository = Depends(dependencies.get_tokens_repository),
    rate_limit_repository: RateLimitRepository = Depends(
        dependencies.get_rate_limit_repository
    ),
    billing_repository: BillingRepository = Depends(
        dependencies.get_billing_repository
    ),
):
    return await rate_limit_service.execute(
        user, tokens_repository, rate_limit_repository, billing_repository
    )
