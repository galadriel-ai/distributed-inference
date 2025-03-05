from uuid import UUID

from distributedinference.domain.agent import get_dashboard_details_use_case
from distributedinference.repository.agent_explorer_repository import (
    AgentExplorerRepository,
)
from distributedinference.service.agent_explorer.entities import AgentDetailsResponse


async def execute(
    agent_instance_id: UUID,
    agent_repository: AgentExplorerRepository,
) -> AgentDetailsResponse:
    agent = await get_dashboard_details_use_case.execute(
        agent_instance_id, agent_repository
    )
    return AgentDetailsResponse(
        instance_id=agent.id,
        name=agent.name,
        docker_image=agent.docker_image,
        is_deleted=agent.is_deleted,
        created_at=int(agent.created_at.timestamp()),
    )
