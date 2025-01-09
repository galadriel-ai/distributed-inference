from distributedinference.domain.user.entities import User
from distributedinference.domain.agent import create_agent_use_case
from distributedinference.domain.agent.entities import CreateAgentInput
from distributedinference.repository.agent_repository import AgentRepository
from distributedinference.service.agent.entities import CreateAgentRequest
from distributedinference.service.agent.entities import CreateAgentResponse


async def execute(
    repository: AgentRepository, user: User, request: CreateAgentRequest
) -> CreateAgentResponse:
    input = CreateAgentInput(
        user_id=user.uid,
        name=request.name,
        docker_image=request.docker_image,
        env_vars=request.env_vars,
    )
    output = await create_agent_use_case.execute(repository, input)

    # TODO launch the TEE instance here?
    return CreateAgentResponse(agent_id=output.agent_id)
