from uuid import UUID

from distributedinference.domain.user.entities import User
from distributedinference.domain.agent import get_agent_use_case
from distributedinference.domain.agent import delete_agent_use_case
from distributedinference.repository.agent_repository import AgentRepository
from distributedinference.service import error_responses
from distributedinference.service.agent.entities import DeleteAgentResponse


async def execute(
    repository: AgentRepository, user: User, agent_id: UUID
) -> DeleteAgentResponse:
    agent = await get_agent_use_case.execute(repository, agent_id)
    if agent is None or agent.user_profile_id != user.uid:
        raise error_responses.NotFoundAPIError("Agent not found")

    await delete_agent_use_case.execute(repository, agent_id, user.uid)
    # TODO stop any running TEE instances
    return DeleteAgentResponse()
