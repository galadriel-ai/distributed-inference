from uuid import UUID

from distributedinference.domain.agent.entities import Agent
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
    tee = await repository.create_tee(
        tee_name=agent.name,
        docker_hub_image=agent.docker_image,
        env_vars=agent.env_vars,
    )
    await agent_repository.insert_agent_instance(
        agent_id=agent.id, enclave_cid=tee.enclave_cid
    )
    return tee
