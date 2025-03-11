from uuid import UUID

from distributedinference.repository.agent_repository import AgentRepository
from distributedinference.repository.tee_orchestration_repository import (
    TeeOrchestrationRepository,
)
from distributedinference.service import error_responses


async def execute(
    agent_id: UUID,
    agent_repository: AgentRepository,
    tee_orchestration_repository: TeeOrchestrationRepository,
) -> str:
    agent_instance = await agent_repository.get_agent_instance(agent_id)
    if not agent_instance:
        raise error_responses.NotFoundAPIError(
            f"Agent instance for agent {agent_id} not found."
        )
    attestation = await tee_orchestration_repository.get_attestation(
        agent_instance.tee_host_base_url, agent_instance.id
    )
    if not attestation:
        raise error_responses.NotFoundAPIError("Agent attestation not found.")
    # Ideally would cache this
    return attestation
