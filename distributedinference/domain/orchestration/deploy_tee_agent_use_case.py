from uuid import UUID
from uuid_extensions import uuid7

from distributedinference.domain.orchestration.entities import TEE
from distributedinference.repository.agent_repository import AgentRepository
from distributedinference.repository.tee_orchestration_repository import (
    TeeOrchestrationRepository,
)


async def execute(
    repository: TeeOrchestrationRepository,
    agent_repository: AgentRepository,
    agent_id: UUID,
) -> TEE:
    agent = await agent_repository.get_agent(agent_id)
    if agent is None:
        raise ValueError(f"Agent with id {agent_id} does not exist")
    agent_instance = await agent_repository.get_agent_instance(agent_id)
    if agent_instance:
        raise ValueError(f"Agent with id {agent_id} already has a TEE instance")
    agent_instance_id = uuid7()
    tee = await repository.create_tee(
        tee_name=str(agent_instance_id),
        docker_hub_image=agent.docker_image,
        env_vars=agent.env_vars,
    )
    await agent_repository.insert_agent_instance(
        agent_id=agent.id,
        agent_instance_id=agent_instance_id,
        enclave_cid=tee.enclave_cid,
    )
    return tee
