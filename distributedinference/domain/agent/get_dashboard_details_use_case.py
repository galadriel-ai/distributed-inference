from uuid import UUID

from distributedinference.domain.agent.entities import DeployedAgentDetails
from distributedinference.repository.agent_explorer_repository import (
    AgentExplorerRepository,
)
from distributedinference.service import error_responses


async def execute(
    agent_instance_id: UUID,
    agent_repository: AgentExplorerRepository,
) -> DeployedAgentDetails:
    agent = await agent_repository.get_agent_instance(agent_instance_id)
    if not agent:
        raise error_responses.NotFoundAPIError()
    return agent
