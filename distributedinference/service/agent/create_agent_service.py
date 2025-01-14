from distributedinference.domain.user.entities import User
from distributedinference.domain.agent import create_agent_use_case
from distributedinference.domain.agent.entities import CreateAgentInput
from distributedinference.domain.orchestration import deploy_tee_agent_use_case
from distributedinference.repository.agent_repository import AgentRepository
from distributedinference.repository.tee_orchestration_repository import (
    TeeOrchestrationRepository,
)
from distributedinference.service.agent.entities import CreateAgentRequest
from distributedinference.service.agent.entities import CreateAgentResponse


async def execute(
    repository: AgentRepository,
    tee_orchestration_repository: TeeOrchestrationRepository,
    user: User,
    request: CreateAgentRequest,
) -> CreateAgentResponse:
    input = CreateAgentInput(
        user_id=user.uid,
        name=request.name,
        docker_image=request.docker_image,
        env_vars=request.env_vars,
    )
    output = await create_agent_use_case.execute(repository, input)

    # launch the agent in a TEE
    await deploy_tee_agent_use_case.execute(
        tee_orchestration_repository, repository, output.agent
    )

    return CreateAgentResponse(agent_id=output.agent.id)
