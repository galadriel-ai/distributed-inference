from typing import List

from distributedinference.domain.agent import get_dashboard_use_case
from distributedinference.domain.agent.entities import DeployedAgent
from distributedinference.repository.agent_explorer_repository import (
    AgentExplorerRepository,
)
from distributedinference.service.agent_explorer.entities import AgentExplorerResponse
from distributedinference.service.agent_explorer.entities import DeployedAgentModel


async def execute(
    agent_repository: AgentExplorerRepository,
) -> AgentExplorerResponse:
    response = await get_dashboard_use_case.execute(agent_repository)
    return AgentExplorerResponse(
        agent_count=response.agent_count,
        node_count=response.node_count,
        uptime_24h=response.uptime_24h,
        latest_agents=_map_latest_agents(response.latest_agents),
    )


def _map_latest_agents(
    latest_agents: List[DeployedAgent],
) -> List[DeployedAgentModel]:
    return [
        DeployedAgentModel(
            agent_id=i.id,
            name=i.name,
            docker_image=i.docker_image,
            created_at=int(i.created_at.timestamp()),
        )
        for i in latest_agents
    ]
