from typing import List

from distributedinference.domain.agent.entities import DeployedAgent
from distributedinference.repository.agent_explorer_repository import (
    AgentExplorerRepository,
)


async def execute(
    name_search: str,
    agent_repository: AgentExplorerRepository,
) -> List[DeployedAgent]:
    return await agent_repository.search_agents(name_search)
