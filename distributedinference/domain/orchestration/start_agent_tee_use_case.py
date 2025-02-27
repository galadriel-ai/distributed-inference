from distributedinference import api_logger
from distributedinference.domain.agent.entities import Agent
from distributedinference.domain.orchestration.entities import TEE
from distributedinference.domain.orchestration import get_tee_instance_status_use_case
from distributedinference.repository.agent_repository import AgentRepository
from distributedinference.repository.tee_orchestration_repository import (
    TeeOrchestrationRepository,
)

logger = api_logger.get()


async def execute(
    repository: TeeOrchestrationRepository,
    agent_repository: AgentRepository,
    agent: Agent,
) -> None:
    agent_instance = await agent_repository.get_agent_instance(agent.id)
    if not agent_instance:
        raise ValueError(
            f"Agent {agent.id} does not have an instance, deployment failed?"
        )
    status = await get_tee_instance_status_use_case.execute(
        repository, str(agent_instance.id)
    )
    if status:
        logger.info(f"Agent {agent.id} already has a TEE running.")
        return

    env_vars = agent.env_vars.copy()
    env_vars.update(agent_instance.instance_env_vars)

    try:
        await repository.create_tee(
            tee_name=str(agent_instance.id),
            docker_hub_image=agent.docker_image,
            env_vars=env_vars,
        )
    except Exception as e:
        raise ValueError(f"Failed to start TEE for agent {agent.id}: {e}")
