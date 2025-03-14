from distributedinference import api_logger
from distributedinference.domain.agent.entities import Agent
from distributedinference.domain.orchestration import exceptions
from distributedinference.repository.agent_repository import AgentRepository
from distributedinference.repository.tee_orchestration_repository import (
    TeeOrchestrationRepository,
)
from distributedinference.repository.aws_storage_repository import AWSStorageRepository
from distributedinference.domain.orchestration import utils

logger = api_logger.get()


async def execute(
    repository: TeeOrchestrationRepository,
    agent_repository: AgentRepository,
    agent: Agent,
) -> None:
    """
    Stop a TEE instance for the given agent and optionally clean up associated resources.

    Args:
        repository (TeeOrchestrationRepository): Repository for TEE operations
        agent_repository (AgentRepository): Repository for agent operations
        agent (Agent): The agent whose TEE instance should be stopped

    Raises:
        AgentInstanceNotFoundError: If the agent doesn't have a running instance

    Returns:
        None
    """
    agent_instance = await agent_repository.get_agent_instance(agent.id)
    if not agent_instance:
        raise exceptions.AgentInstanceNotFoundError(
            f"Agent with id {agent.id} doesn't have a running instance"
        )
    tee = utils.agent_instance_to_tee(agent_instance)
    try:
        await repository.delete_tee(tee)
    except Exception as e:
        # Probably the TEE is already stopped, ignore the error, but log it
        logger.error(f"Error deleting TEE: {e}")
    await agent_repository.delete_agent_instance(agent_instance.id)
