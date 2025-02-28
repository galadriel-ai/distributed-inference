from typing import Annotated
from typing import Literal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Path
from fastapi import Query
from fastapi import Request

import settings
from distributedinference import api_logger
from distributedinference import dependencies
from distributedinference.analytics.analytics import Analytics
from distributedinference.analytics.analytics import AnalyticsEvent
from distributedinference.analytics.analytics import EventName
from distributedinference.domain.user.entities import User
from distributedinference.repository.agent_logs_repository import AgentLogsRepository
from distributedinference.repository.agent_repository import AgentRepository
from distributedinference.repository.aws_storage_repository import AWSStorageRepository
from distributedinference.repository.tee_orchestration_repository import (
    TeeOrchestrationRepository,
)
from distributedinference.service.agent import chat_to_agent_service
from distributedinference.service.agent import create_agent_service
from distributedinference.service.agent import delete_agent_service
from distributedinference.service.agent import get_agent_service
from distributedinference.service.agent import get_user_agents_service
from distributedinference.service.agent import update_agent_service
from distributedinference.service.agent.entities import AddLogsRequest
from distributedinference.service.agent.entities import AddLogsResponse
from distributedinference.service.agent.entities import CreateAgentRequest
from distributedinference.service.agent.entities import CreateAgentResponse
from distributedinference.service.agent.entities import DeleteAgentResponse
from distributedinference.service.agent.entities import GetAgentResponse
from distributedinference.service.agent.entities import GetAgentsResponse
from distributedinference.service.agent.entities import GetLogsRequest
from distributedinference.service.agent.entities import GetLogsResponse
from distributedinference.service.agent.entities import SUPPORTED_LOG_LEVELS_TYPE
from distributedinference.service.agent.entities import UpdateAgentRequest
from distributedinference.service.agent.entities import UpdateAgentResponse
from distributedinference.service.agent.logs import add_agent_logs_service
from distributedinference.service.agent.logs import get_agent_logs_service
from distributedinference.service.auth import authentication

TAG = "Agent"
router = APIRouter(prefix="/agents")
router.tags = [TAG]

logger = api_logger.get()


@router.get(
    "/",
    summary="Gets all agents for the user",
    description="",
    response_description="Agent information",
    response_model=GetAgentsResponse,
)
async def get_user_agents(
    user: User = Depends(authentication.validate_api_key_header),
    agent_repository: AgentRepository = Depends(dependencies.get_agent_repository),
):
    return await get_user_agents_service.execute(agent_repository, user)


@router.get(
    "/{agent_id}",
    summary="Gets agent information",
    description="",
    response_description="Agent information",
    response_model=GetAgentResponse,
)
async def get_agent(
    agent_id: Annotated[UUID, Path(..., description="Agent ID")],
    user: User = Depends(authentication.validate_api_key_header),
    agent_repository: AgentRepository = Depends(dependencies.get_agent_repository),
):
    return await get_agent_service.execute(agent_repository, user, agent_id)


# pylint: disable=too-many-arguments
@router.post(
    "/",
    summary="Creates a new agent",
    description="",
    response_description="Agent ID",
    response_model=CreateAgentResponse,
)
async def create_agent(
    request: CreateAgentRequest,
    user: User = Depends(authentication.validate_api_key_header),
    agent_repository: AgentRepository = Depends(dependencies.get_agent_repository),
    tee_orchestration_repository: TeeOrchestrationRepository = Depends(
        dependencies.get_tee_orchestration_repository
    ),
    aws_storage_repository: AWSStorageRepository = Depends(
        dependencies.get_aws_storage_repository
    ),
    analytics: Analytics = Depends(dependencies.get_analytics),
):
    response = await create_agent_service.execute(
        agent_repository,
        tee_orchestration_repository,
        aws_storage_repository,
        user,
        request,
    )
    analytics.track_event(
        user.uid,
        AnalyticsEvent(EventName.CREATE_AGENT, {"agent_id": response.agent_id}),
    )
    return response


@router.put(
    "/{agent_id}",
    summary="Updates an agent",
    description="",
    response_description="Agent ID",
    response_model=UpdateAgentResponse,
)
async def update_agent(
    request: UpdateAgentRequest,
    agent_id: Annotated[UUID, Path(..., description="Agent ID")],
    user: User = Depends(authentication.validate_api_key_header),
    agent_repository: AgentRepository = Depends(dependencies.get_agent_repository),
    analytics: Analytics = Depends(dependencies.get_analytics),
):
    response = await update_agent_service.execute(
        agent_repository, user, agent_id, request
    )
    analytics.track_event(
        user.uid,
        AnalyticsEvent(EventName.UPDATE_AGENT, {"agent_id": agent_id}),
    )
    return response


# pylint: disable=too-many-arguments
@router.delete(
    "/{agent_id}",
    summary="Deletes an agent",
    description="",
    response_description="Agent ID",
    response_model=DeleteAgentResponse,
)
async def delete_agent(
    agent_id: Annotated[UUID, Path(..., description="Agent ID")],
    user: User = Depends(authentication.validate_api_key_header),
    agent_repository: AgentRepository = Depends(dependencies.get_agent_repository),
    tee_orchestration_repository: TeeOrchestrationRepository = Depends(
        dependencies.get_tee_orchestration_repository
    ),
    aws_storage_repository: AWSStorageRepository = Depends(
        dependencies.get_aws_storage_repository
    ),
    analytics: Analytics = Depends(dependencies.get_analytics),
):
    response = await delete_agent_service.execute(
        agent_repository,
        tee_orchestration_repository,
        aws_storage_repository,
        user,
        agent_id,
    )
    analytics.track_event(
        user.uid,
        AnalyticsEvent(EventName.DELETE_AGENT, {"agent_id": agent_id}),
    )
    return response


@router.post(
    "/logs/{agent_id}",
    summary="Append agent logs",
    description="Append-only agent logs addition",
    response_description="Agent ID",
    response_model=AddLogsResponse,
    include_in_schema=not settings.is_production(),
)
# Endpoint "authentication" is checked in IpWhitelistMiddleware
async def add_logs(
    agent_id: Annotated[UUID, Path(..., description="Agent ID")],
    request: AddLogsRequest,
    user: User = Depends(authentication.validate_api_key_header),
    agent_repository: AgentRepository = Depends(dependencies.get_agent_repository),
    logs_repository: AgentLogsRepository = Depends(
        dependencies.get_agent_logs_repository
    ),
):
    return await add_agent_logs_service.execute(
        agent_id, request, user, agent_repository, logs_repository
    )


@router.get(
    "/logs/{agent_id}",
    summary="Get agent logs",
    description="Get agent logs, newest first",
    response_description="Agent ID",
    response_model=GetLogsResponse,
    include_in_schema=not settings.is_production(),
)
async def get_logs(
    # pylint: disable=R0913
    agent_id: Annotated[UUID, Path(..., description="Agent ID")],
    limit: Optional[int] = Query(
        50, description="The maximum number of logs to retrieve."
    ),
    level: Optional[Literal[SUPPORTED_LOG_LEVELS_TYPE]] = Query(
        "info", description='Log level, "thought" returns only "though" level logs'
    ),
    cursor: Optional[UUID] = Query(None, description="The cursor for pagination."),
    user: User = Depends(authentication.validate_api_key_header),
    agent_repository: AgentRepository = Depends(dependencies.get_agent_repository),
    logs_repository: AgentLogsRepository = Depends(
        dependencies.get_agent_logs_repository
    ),
):
    request = GetLogsRequest(
        agent_id=agent_id,
        limit=limit,
        level=level,
        cursor=cursor,
    )
    return await get_agent_logs_service.execute(
        request,
        user,
        agent_repository,
        logs_repository,
    )


@router.post(
    "/{agent_id}/chat/completions",
    summary="Proxy chat completions to agent instance",
    description="Forwards chat completion requests to the agent's TEE instance",
    response_description="Streaming response from the agent instance",
)
async def chat_completions(
    request: Request,
    agent_id: Annotated[UUID, Path(..., description="Agent ID")],
    user: User = Depends(authentication.validate_api_key_header),
    agent_repository: AgentRepository = Depends(dependencies.get_agent_repository),
):
    """
    Proxy chat completion requests to the agent's TEE instance.

    This endpoint forwards requests to the TEE instance running the agent,
    supporting streaming responses for chat completions.

    Args:
        request: The incoming request
        agent_id: The ID of the agent
        user: The authenticated user
        agent_repository: Repository for agent operations

    Returns:
        Streaming response from the agent instance

    Raises:
        HTTPException: If the agent doesn't exist, doesn't belong to the user,
                      doesn't have a running instance, or if the proxy request fails
    """
    return await chat_to_agent_service.execute(
        request,
        agent_id,
        user,
        agent_repository,
    )
