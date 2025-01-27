from distributedinference.domain.agent.entities import Agent
from distributedinference.domain.orchestration.entities import TEE
from distributedinference.repository.agent_repository import AgentRepository
from distributedinference.repository.tee_orchestration_repository import (
    TeeOrchestrationRepository,
)
from distributedinference.repository.aws_storage_repository import AWSStorageRepository


async def execute(
    repository: TeeOrchestrationRepository,
    agent_repository: AgentRepository,
    aws_storage_repository: AWSStorageRepository,
    agent: Agent,
) -> None:
    agent_instance = await agent_repository.get_agent_instance(agent.id)
    if not agent_instance:
        raise ValueError(f"Agent with id {agent.id} doesn't have a TEE instance")
    await repository.delete_tee(str(agent_instance.id))
    await aws_storage_repository.cleanup_user_and_bucket_access(str(agent_instance.id))
    await agent_repository.delete_agent_instance(
        agent_instance.id,
    )
