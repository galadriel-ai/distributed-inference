from typing import List

from distributedinference.domain.agent import search_agents_use_case
from distributedinference.domain.agent.entities import DeployedAgent
from distributedinference.repository.agent_explorer_repository import (
    AgentExplorerRepository,
)
from distributedinference.service.agent_explorer.entities import AgentSearchResponse
from distributedinference.service.agent_explorer.entities import DeployedAgentModel


async def execute(
    name_search: str,
    agent_repository: AgentExplorerRepository,
) -> AgentSearchResponse:
    agents = await search_agents_use_case.execute(name_search, agent_repository)
    return AgentSearchResponse(
        agents=_map_latest_agents(agents),
    )


def _map_latest_agents(
    agents: List[DeployedAgent],
) -> List[DeployedAgentModel]:
    return [
        DeployedAgentModel(
            agent_id=i.id,
            name=i.name,
            docker_image=i.docker_image,
            created_at=int(i.created_at.timestamp()),
        )
        for i in agents
    ]
