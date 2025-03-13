from uuid import UUID

from distributedinference.domain.user.entities import User
from distributedinference.domain.agent import get_agent_use_case
from distributedinference.domain.agent import delete_agent_use_case
from distributedinference.domain.orchestration import exceptions
from distributedinference.domain.orchestration import stop_agent_tee_use_case
from distributedinference.repository.agent_repository import AgentRepository
from distributedinference.repository.tee_orchestration_repository import (
    TeeOrchestrationRepository,
)
from distributedinference.repository.aws_storage_repository import AWSStorageRepository
from distributedinference.service import error_responses
from distributedinference.service.agent.entities import DeleteAgentResponse


async def execute(
    repository: AgentRepository,
    tee_orchestration_repository: TeeOrchestrationRepository,
    aws_storage_repository: AWSStorageRepository,
    user: User,
    agent_id: UUID,
) -> DeleteAgentResponse:
    agent = await get_agent_use_case.execute(repository, agent_id)
    if agent is None or agent.user_profile_id != user.uid:
        raise error_responses.NotFoundAPIError("Agent not found")

    try:
        await stop_agent_tee_use_case.execute(
            tee_orchestration_repository,
            repository,
            aws_storage_repository,
            agent,
            delete_agent_instance=True,
        )
    except exceptions.AgentInstanceNotFoundError:
        # If the agent instance is not found, it means the TEE is already stopped
        pass
    await delete_agent_use_case.execute(repository, agent_id)
    return DeleteAgentResponse()
