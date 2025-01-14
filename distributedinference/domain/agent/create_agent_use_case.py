from distributedinference.domain.agent.entities import Agent
from distributedinference.domain.agent.entities import CreateAgentInput
from distributedinference.domain.agent.entities import CreateAgentOutput
from distributedinference.repository.agent_repository import AgentRepository
from distributedinference.repository.utils import utcnow


async def execute(
    repository: AgentRepository, input: CreateAgentInput
) -> CreateAgentOutput:
    agent_id = await repository.insert_agent(
        user_id=input.user_id,
        name=input.name,
        docker_image=input.docker_image,
        env_vars=input.env_vars,
    )
    agent = Agent(
        id=agent_id,
        name=input.name,
        created_at=utcnow(),
        docker_image=input.docker_image,
        env_vars=input.env_vars,
        last_updated_at=utcnow(),
        user_profile_id=input.user_id,
    )
    return CreateAgentOutput(agent=agent)
