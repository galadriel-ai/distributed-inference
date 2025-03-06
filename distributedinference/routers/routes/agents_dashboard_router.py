from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Path

import settings
from distributedinference import dependencies
from distributedinference.repository.agent_explorer_repository import (
    AgentExplorerRepository,
)
from distributedinference.service.agent_explorer import agent_details_service
from distributedinference.service.agent_explorer import agent_explorer_service
from distributedinference.service.agent_explorer.entities import AgentDetailsResponse
from distributedinference.service.agent_explorer.entities import AgentExplorerResponse

TAG = "Agents dashboard"
router = APIRouter(prefix="/agent-dashboard")
router.tags = [TAG]


# TODO: do we want some sort of validation for these endpoints?
#  eg only callable from the explorer frontend?


@router.get(
    "",
    summary="Returns Agent TEE explorer landing page info.",
    description="Returns all the relevant info for the agent TEE explorer landing page.",
    response_description="",
    response_model=AgentExplorerResponse,
    include_in_schema=not settings.is_production(),
)
async def agents(
    agent_repository: AgentExplorerRepository = Depends(
        dependencies.get_agent_explorer_repository
    ),
):
    return await agent_explorer_service.execute(agent_repository)


@router.get(
    "/{agent_id}",
    summary="Returns Agent TEE instance details.",
    description="Returns deployed agent info.",
    response_description="",
    response_model=AgentDetailsResponse,
    include_in_schema=not settings.is_production(),
)
async def agent_details(
    agent_id: Annotated[UUID, Path(..., description="Agent ID")],
    agent_repository: AgentExplorerRepository = Depends(
        dependencies.get_agent_explorer_repository
    ),
):
    return await agent_details_service.execute(agent_id, agent_repository)
