from uuid import UUID
from typing import List

from distributedinference.domain.agent.entities import Agent
from distributedinference.repository.agent_repository import AgentRepository


async def execute(repository: AgentRepository, user_profile_id: UUID) -> List[Agent]:
    return await repository.get_user_agents(user_profile_id)
