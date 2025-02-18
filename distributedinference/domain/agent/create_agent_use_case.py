from distributedinference.domain.agent.entities import Agent
from distributedinference.domain.agent.entities import CreateAgentInput
from distributedinference.domain.agent.entities import CreateAgentOutput
from distributedinference.repository.agent_repository import AgentRepository
from distributedinference.repository.utils import utcnow


async def execute(
    repository: AgentRepository, input: CreateAgentInput
) -> CreateAgentOutput:
    """
    Execute the use case for creating a new agent.

    This asynchronous function performs the following steps:
      1. Inserts the primary agent record into the repository.
      2. Inserts the initial agent version linked to the newly created agent.
      3. Constructs an Agent entity with the provided input parameters and the current UTC timestamps.
      4. Returns a CreateAgentOutput that encapsulates the created agent entity.

    Args:
        repository (AgentRepository): The repository instance responsible for persisting
                                      the agent data.
        input (CreateAgentInput): The input data required to create an agent, including:
            - user_id: Identifier of the user owning the agent.
            - name: Name of the agent.
            - docker_image: Docker image used for the agent.
            - env_vars: Environment variables for the agent.
            - docker_image_hash: The hash of the docker image.

    Returns:
        CreateAgentOutput: An output object containing the newly created Agent entity.
    """
    agent_id = await repository.insert_agent(
        user_id=input.user_id,
        name=input.name,
        docker_image=input.docker_image,
        docker_image_hash=input.docker_image_hash,
        env_vars=input.env_vars,
    )
    await repository.insert_agent_version(
        agent_id=agent_id,
        docker_image=input.docker_image,
        docker_image_hash=input.docker_image_hash,
        env_vars=input.env_vars,
    )
    agent = Agent(
        id=agent_id,
        name=input.name,
        created_at=utcnow(),
        docker_image=input.docker_image,
        docker_image_hash=input.docker_image_hash,
        env_vars=input.env_vars,
        last_updated_at=utcnow(),
        user_profile_id=input.user_id,
    )
    return CreateAgentOutput(agent=agent)
