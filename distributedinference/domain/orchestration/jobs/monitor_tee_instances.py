import asyncio
from uuid import UUID

import settings
from distributedinference import api_logger
from distributedinference.repository.agent_repository import AgentRepository
from distributedinference.repository.tee_orchestration_repository import (
    TeeOrchestrationRepository,
)

logger = api_logger.get()


async def execute(
    agent_repository: AgentRepository,
    tee_orchestration_repository: TeeOrchestrationRepository,
) -> None:
    while True:
        try:
            await asyncio.sleep(settings.TEE_MONITORING_TIMEOUT_BETWEEN_RUNS_SECONDS)
            logger.info("Checking running agent TEEs")
            agents = await agent_repository.get_all_agents()
            agent_instances = await agent_repository.get_agent_instances()
            tees = await tee_orchestration_repository.get_all_tees()

            instances_by_agent_id = {
                instance.agent_id: instance for instance in agent_instances
            }
            tees_by_agent_instance_id = {UUID(tee.enclave_name): tee for tee in tees}
            for agent in agents:
                tee = None
                agent_instance = instances_by_agent_id.get(agent.id)
                if not agent_instance:
                    logger.info(
                        f"Agent {agent.id} does not have an instance, will not check TEE status."
                    )
                    continue
                tee = tees_by_agent_instance_id.get(agent_instance.id)
                if not tee:
                    logger.info(
                        f"Agent {agent.id} does not have a TEE running. Starting one."
                    )
                    tee = await tee_orchestration_repository.create_tee(
                        tee_name=str(agent_instance.id),
                        docker_hub_image=agent.docker_image,
                        env_vars=agent.env_vars,
                    )
                else:
                    logger.info(f"Agent {agent.id} has a TEE running.")

        except Exception as e:
            logger.error(f"Error checking running agent TEEs: {str(e)}")
