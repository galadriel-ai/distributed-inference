from uuid import UUID

from distributedinference.domain.agent.entities import DeployedAgentDetails
from distributedinference.repository.agent_explorer_repository import (
    AgentExplorerRepository,
)
from distributedinference.service import error_responses


async def execute(
    agent_id: UUID,
    agent_repository: AgentExplorerRepository,
) -> DeployedAgentDetails:
    agent = await agent_repository.get_agent(agent_id)
    if not agent:
        raise error_responses.NotFoundAPIError()
    agent_instances = await agent_repository.get_agent_instances(agent_id)
    return DeployedAgentDetails(
        id=agent.id,
        name=agent.name,
        docker_image=agent.docker_image,
        metadata=agent.metadata,
        created_at=agent.created_at,
        agent_instances=agent_instances,
    )
