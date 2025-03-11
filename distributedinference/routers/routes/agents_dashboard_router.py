from typing import Annotated
from typing import Optional
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Path
from fastapi import Query

import settings
from distributedinference import dependencies
from distributedinference.repository.agent_explorer_repository import (
    AgentExplorerRepository,
)
from distributedinference.repository.agent_repository import AgentRepository
from distributedinference.repository.tee_orchestration_repository import (
    TeeOrchestrationRepository,
)
from distributedinference.service.agent_explorer import agent_attestation_service
from distributedinference.service.agent_explorer import agent_details_service
from distributedinference.service.agent_explorer import (
    agent_explorer_all_agents_service,
)
from distributedinference.service.agent_explorer import agent_explorer_search_service
from distributedinference.service.agent_explorer import agent_explorer_service
from distributedinference.service.agent_explorer.entities import (
    AgentAttestationResponse,
)
from distributedinference.service.agent_explorer.entities import AgentDetailsResponse
from distributedinference.service.agent_explorer.entities import AgentExplorerResponse
from distributedinference.service.agent_explorer.entities import AgentSearchResponse
from distributedinference.service.agent_explorer.entities import AllAgentsResponse

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
async def dashboard(
    agent_repository: AgentExplorerRepository = Depends(
        dependencies.get_agent_explorer_repository
    ),
):
    return await agent_explorer_service.execute(agent_repository)


@router.get(
    "/agents",
    summary="Get all agents.",
    description="Returns paginated agents.",
    response_description="",
    response_model=AllAgentsResponse,
    include_in_schema=not settings.is_production(),
)
async def agents(
    cursor: Optional[str] = Query(None, description="Cursor for pagination"),
    agent_repository: AgentExplorerRepository = Depends(
        dependencies.get_agent_explorer_repository
    ),
):
    return await agent_explorer_all_agents_service.execute(cursor, agent_repository)


@router.get(
    "/search",
    summary="Search agents by name.",
    description="Returns search results.",
    response_description="",
    response_model=AgentSearchResponse,
    include_in_schema=not settings.is_production(),
)
async def search(
    name: str = Query(..., description="Agent name"),
    agent_repository: AgentExplorerRepository = Depends(
        dependencies.get_agent_explorer_repository
    ),
):
    return await agent_explorer_search_service.execute(name, agent_repository)


@router.get(
    "/agent/{agent_id}",
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


@router.get(
    "/agent/{agent_id}/attestation",
    summary="Returns Agent TEE instance attestation.",
    description="Returns the current up to date attestation file for the TEE.",
    response_description="",
    response_model=AgentAttestationResponse,
    include_in_schema=not settings.is_production(),
)
async def attestation(
    agent_id: Annotated[UUID, Path(..., description="Agent ID")],
    agent_repository: AgentRepository = Depends(dependencies.get_agent_repository),
    tee_orchestration_repository: TeeOrchestrationRepository = Depends(
        dependencies.get_tee_orchestration_repository
    ),
):
    return await agent_attestation_service.execute(
        agent_id, agent_repository, tee_orchestration_repository
    )
