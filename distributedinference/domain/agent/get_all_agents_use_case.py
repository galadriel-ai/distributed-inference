from typing import List
from typing import Optional
from uuid import UUID

from distributedinference.domain.agent.entities import AllAgentsOutput
from distributedinference.domain.agent.entities import DeployedAgent
from distributedinference.repository.agent_explorer_repository import (
    AgentExplorerRepository,
)

COUNT = 20


async def execute(
    cursor: Optional[str],
    agent_repository: AgentExplorerRepository,
) -> AllAgentsOutput:
    agents = await agent_repository.get_latest_agents(cursor=cursor, count=COUNT)
    return AllAgentsOutput(agents=agents, cursor=_get_cursor(agents))


def _get_cursor(agents: List[DeployedAgent]) -> Optional[UUID]:
    if len(agents) == COUNT:
        return agents[-1].id
    return None
