from uuid import UUID


from distributedinference.domain.user.entities import User
from distributedinference.domain.agent import get_agent_use_case
from distributedinference.domain.agent import update_agent_use_case
from distributedinference.domain.agent.entities import UpdateAgentInput
from distributedinference.repository.agent_repository import AgentRepository
from distributedinference.service import error_responses
from distributedinference.service.agent.entities import UpdateAgentRequest
from distributedinference.service.agent.entities import UpdateAgentResponse


async def execute(
    repository: AgentRepository, user: User, agent_id: UUID, request: UpdateAgentRequest
) -> UpdateAgentResponse:
    agent = await get_agent_use_case.execute(repository, agent_id)
    if agent is None or agent.user_profile_id != user.uid:
        raise error_responses.NotFoundAPIError("Agent not found")

    input = UpdateAgentInput(
        agent_id=agent_id,
        name=request.name,
        docker_image=request.docker_image,
        docker_image_hash=request.docker_image_hash,
        env_vars=request.env_vars,
    )
    await update_agent_use_case.execute(repository, input)
    # TODO: update the agent instance here
    return UpdateAgentResponse()
