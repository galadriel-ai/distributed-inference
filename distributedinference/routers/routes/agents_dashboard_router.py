from fastapi import APIRouter
from fastapi import Depends

import settings
from distributedinference import dependencies
from distributedinference.repository.agent_explorer_repository import (
    AgentExplorerRepository,
)
from distributedinference.service.agent_explorer import agent_explorer_service
from distributedinference.service.agent_explorer.entities import AgentExplorerResponse

TAG = "Agents dashboard"
router = APIRouter(prefix="/agent-dashboard")
router.tags = [TAG]


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
    # TODO: do we want some sort of validation for this endpoint?
    #  eg only callable from the explorer frontend?
    return await agent_explorer_service.execute(agent_repository)
