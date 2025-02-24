from distributedinference.domain.agent.entities import UpdateAgentInput
from distributedinference.repository.agent_repository import AgentRepository


async def execute(repository: AgentRepository, input: UpdateAgentInput) -> None:
    """
    Update an agent's details and insert a new agent version into the repository.

    This function performs two operations:
      1. It updates the agent's metadata in the repository using provided information.
      2. It inserts a new version record for the agent, which helps in tracking changes over time.

    Args:
        repository (AgentRepository): The repository instance for handling agent data operations.
        input (UpdateAgentInput): An entity containing updated agent details such as agent_id,
                                  name, docker_image, docker_image_hash, and env_vars.

    Returns:
        None
    """
    await repository.update_agent(
        agent_id=input.agent_id,
        name=input.name,
        docker_image=input.docker_image,
        docker_image_hash=input.docker_image_hash,
        env_vars=input.env_vars,
    )
    await repository.insert_agent_version(
        agent_id=input.agent_id,
        docker_image=input.docker_image,
        docker_image_hash=input.docker_image_hash,
        env_vars=input.env_vars,
    )
