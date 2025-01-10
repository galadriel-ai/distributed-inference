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

            tees_by_agent_id = {UUID(tee.enclave_name): tee for tee in tees}
            for agent in agents:
                tee = tees_by_agent_id.get(agent.id)
                if not tee:
                    logger.info(
                        f"Agent {agent.id} does not have a TEE running. Starting one."
                    )
                    tee = await tee_orchestration_repository.create_tee(
                        tee_name=str(agent.id),
                        docker_hub_image=agent.docker_image,
                        env_vars=agent.env_vars,
                    )
                    await agent_repository.insert_agent_instance(
                        agent_id=agent.id, enclave_cid=tee.enclave_cid
                    )
                else:
                    logger.info(f"Agent {agent.id} has a TEE running.")

        except Exception as e:
            logger.error(f"Error checking running agent TEEs: {str(e)}")
