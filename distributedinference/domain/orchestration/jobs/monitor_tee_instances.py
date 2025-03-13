import asyncio
from uuid import UUID

import settings
from distributedinference import api_logger
from distributedinference.domain.orchestration import get_running_tees_use_case
from distributedinference.repository.agent_repository import AgentRepository
from distributedinference.repository.aws_storage_repository import AWSStorageRepository
from distributedinference.repository.tee_orchestration_repository import (
    TeeOrchestrationRepository,
)

logger = api_logger.get()


async def execute(
    agent_repository: AgentRepository,
    tee_orchestration_repository: TeeOrchestrationRepository,
    aws_storage_repository: AWSStorageRepository,
) -> None:
    while True:
        try:
            await asyncio.sleep(settings.TEE_MONITORING_TIMEOUT_BETWEEN_RUNS_SECONDS)
            logger.info("Checking agent instances")
            await _check_agent_instances(
                agent_repository, tee_orchestration_repository, aws_storage_repository
            )
        except Exception as e:
            logger.error(f"Error checking running agent TEEs: {str(e)}")


async def _check_agent_instances(
    agent_repository: AgentRepository,
    tee_orchestration_repository: TeeOrchestrationRepository,
    aws_storage_repository: AWSStorageRepository,
) -> None:
    agent_instances = await agent_repository.get_agent_instances(is_deleted=False)
    tees = await get_running_tees_use_case.execute(tee_orchestration_repository)
    tees_by_agent_instance_id = {}
    for tee in tees:
        try:
            tees_by_agent_instance_id[UUID(tee.name)] = tee
        except ValueError:
            logger.error(
                f"TEE {tee.name} does not have a valid UUID, will not be able to match it to an agent instance."
            )
    for agent_instance in agent_instances:
        agent_tee = tees_by_agent_instance_id.get(agent_instance.id)
        if not agent_tee:
            logger.info(
                f"Agent instance {agent_instance.id} does not have a TEE running, deleting it."
            )
            try:
                await agent_repository.delete_agent_instance(agent_instance.id)
                await aws_storage_repository.cleanup_user_and_bucket_access(
                    str(agent_instance.id)
                )
            except Exception as e:
                logger.error(
                    f"Error deleting agent instance {agent_instance.id}: {str(e)}"
                )
