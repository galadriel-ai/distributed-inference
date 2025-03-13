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
    aws_storage_repository: AWSStorageRepository,
    agent: Agent,
    delete_agent_instance: bool = False,
) -> None:
    """
    Stop a TEE instance for the given agent and optionally clean up associated resources.

    Args:
        repository (TeeOrchestrationRepository): Repository for TEE operations
        agent_repository (AgentRepository): Repository for agent operations
        aws_storage_repository (AWSStorageRepository): Repository for AWS storage operations
        agent (Agent): The agent whose TEE instance should be stopped
        delete_agent_instance (bool, optional): Whether to delete the agent instance
            and clean up AWS resources. Defaults to False. This is set to True when the agent is deleted.

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
    if delete_agent_instance:
        await aws_storage_repository.cleanup_user_and_bucket_access(
            str(agent_instance.id)
        )
        await agent_repository.delete_agent_instance(agent_instance.id)
