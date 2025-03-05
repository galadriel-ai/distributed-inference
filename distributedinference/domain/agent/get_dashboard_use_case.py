from distributedinference.domain.agent.entities import AgentExplorerOutput
from distributedinference.repository.agent_explorer_repository import (
    AgentExplorerRepository,
)


async def execute(
    agent_repository: AgentExplorerRepository,
) -> AgentExplorerOutput:
    agent_count = await agent_repository.get_agent_instances_count()
    latest_agents = await agent_repository.get_latest_deployed_agents()
    return AgentExplorerOutput(
        agent_count=agent_count,
        node_count=20,
        uptime_24h=100 * (10**2),
        latest_agents=latest_agents,
    )
