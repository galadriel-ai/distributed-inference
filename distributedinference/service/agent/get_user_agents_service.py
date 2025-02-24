from uuid import UUID

from distributedinference.domain.user.entities import User
from distributedinference.domain.agent import get_user_agents_use_case
from distributedinference.repository.agent_repository import AgentRepository
from distributedinference.service.agent.entities import Agent
from distributedinference.service.agent.entities import GetAgentsResponse


async def execute(repository: AgentRepository, user: User) -> GetAgentsResponse:
    agents = await get_user_agents_use_case.execute(
        repository, user_profile_id=user.uid
    )

    return GetAgentsResponse(
        agents=[
            Agent(
                agent_id=agent.id,
                name=agent.name,
                docker_image=agent.docker_image,
                docker_image_hash=agent.docker_image_hash,
                updated_at=agent.last_updated_at,
                pcr0_hash="mock_hash",
            )
            for agent in agents
        ]
    )
