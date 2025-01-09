from distributedinference.domain.agent.entities import Agent
from distributedinference.domain.agent.entities import UpdateAgentInput
from distributedinference.repository.agent_repository import AgentRepository


async def execute(repository: AgentRepository, input: UpdateAgentInput) -> None:
    await repository.update_agent(
        agent_id=input.agent_id,
        name=input.name,
        docker_image=input.docker_image,
        env_vars=input.env_vars,
    )
