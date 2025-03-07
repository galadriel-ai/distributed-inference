from typing import List
from typing import Optional

from distributedinference.domain.agent import get_all_agents_use_case
from distributedinference.domain.agent.entities import DeployedAgent
from distributedinference.repository.agent_explorer_repository import (
    AgentExplorerRepository,
)
from distributedinference.service.agent_explorer.entities import AllAgentsResponse
from distributedinference.service.agent_explorer.entities import DeployedAgentModel


async def execute(
    cursor: Optional[str],
    agent_repository: AgentExplorerRepository,
) -> AllAgentsResponse:
    response = await get_all_agents_use_case.execute(cursor, agent_repository)
    return AllAgentsResponse(
        agents=_map_latest_agents(response.agents),
        cursor=str(response.cursor) if response.cursor else None,
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
