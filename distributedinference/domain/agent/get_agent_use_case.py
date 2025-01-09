from uuid import UUID
from typing import Optional

from distributedinference.domain.agent.entities import Agent
from distributedinference.repository.agent_repository import AgentRepository


async def execute(repository: AgentRepository, agent_id: UUID) -> Optional[Agent]:
    return await repository.get_agent(agent_id)
