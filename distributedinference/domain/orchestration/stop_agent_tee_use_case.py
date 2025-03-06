from distributedinference.domain.agent.entities import Agent
from distributedinference.repository.agent_repository import AgentRepository
from distributedinference.repository.tee_orchestration_repository import (
    TeeOrchestrationRepository,
)
from distributedinference.repository.aws_storage_repository import AWSStorageRepository
from distributedinference.domain.orchestration import utils


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
        ValueError: If the agent doesn't have an associated TEE instance

    Returns:
        None
    """
    agent_instance = await agent_repository.get_agent_instance(agent.id)
    if not agent_instance:
        raise ValueError(f"Agent with id {agent.id} doesn't have a TEE instance")
    tee = utils.agent_instance_to_tee(agent_instance)
    await repository.delete_tee(tee)
    if delete_agent_instance:
        await aws_storage_repository.cleanup_user_and_bucket_access(
            str(agent_instance.id)
        )
        await agent_repository.delete_agent_instance(agent_instance.id)
