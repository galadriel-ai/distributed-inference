from uuid import UUID

from distributedinference.domain.user.entities import User
from distributedinference.domain.agent import get_agent_use_case
from distributedinference.repository.agent_repository import AgentRepository
from distributedinference.service import error_responses
from distributedinference.service.agent.entities import GetAgentRequest
from distributedinference.service.agent.entities import GetAgentResponse


async def execute(
    repository: AgentRepository, user: User, agent_id: UUID
) -> GetAgentResponse:
    agent = await get_agent_use_case.execute(repository, agent_id)
    if agent is None or agent.user_profile_id != user.uid:
        raise error_responses.NotFoundAPIError("Agent not found")

    # TODO retrieve pcr0 hash from the TEE host service
    return GetAgentResponse(
        agent_id=agent.id,
        name=agent.name,
        updated_at=agent.last_updated_at,
        docker_image=agent.docker_image,
        pcr0_hash="mock_hash",
    )
