from uuid import UUID
from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Path

from distributedinference import api_logger, dependencies
from distributedinference.analytics.analytics import (
    Analytics,
    AnalyticsEvent,
    EventName,
)
from distributedinference.domain.user.entities import User
from distributedinference.repository.agent_repository import AgentRepository
from distributedinference.service.auth import authentication
from distributedinference.service.agent import create_agent_service
from distributedinference.service.agent import delete_agent_service
from distributedinference.service.agent import get_agent_service
from distributedinference.service.agent import update_agent_service
from distributedinference.service.agent.entities import CreateAgentRequest
from distributedinference.service.agent.entities import CreateAgentResponse
from distributedinference.service.agent.entities import DeleteAgentResponse
from distributedinference.service.agent.entities import GetAgentResponse
from distributedinference.service.agent.entities import UpdateAgentRequest
from distributedinference.service.agent.entities import UpdateAgentResponse

TAG = "Agent"
router = APIRouter(prefix="/agent")
router.tags = [TAG]

logger = api_logger.get()


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
    analytics: Analytics = Depends(dependencies.get_analytics),
):
    response = await create_agent_service.execute(agent_repository, user, request)
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
    analytics: Analytics = Depends(dependencies.get_analytics),
):
    response = await delete_agent_service.execute(agent_repository, user, agent_id)
    analytics.track_event(
        user.uid,
        AnalyticsEvent(EventName.DELETE_AGENT, {"agent_id": agent_id}),
    )
    return response
