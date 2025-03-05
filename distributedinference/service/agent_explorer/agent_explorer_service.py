from typing import List

from distributedinference.domain.agent import get_dashboard_use_case
from distributedinference.domain.agent.entities import DeployedAgent
from distributedinference.repository.agent_explorer_repository import (
    AgentExplorerRepository,
)
from distributedinference.service.agent_explorer.entities import AgentExplorerResponse
from distributedinference.service.agent_explorer.entities import DeployedAgentInstance


async def execute(
    agent_repository: AgentExplorerRepository,
) -> AgentExplorerResponse:
    response = await get_dashboard_use_case.execute(agent_repository)
    return AgentExplorerResponse(
        agent_count=response.agent_count,
        node_count=response.node_count,
        uptime_24h=response.uptime_24h,
        latest_instances=_map_latest_instances(response.latest_agents),
    )


def _map_latest_instances(
    latest_agents: List[DeployedAgent],
) -> List[DeployedAgentInstance]:
    return [
        DeployedAgentInstance(
            instance_id=i.id,
            name=i.name,
            docker_image=i.docker_image,
            created_at=int(i.created_at.timestamp()),
        )
        for i in latest_agents
    ]
