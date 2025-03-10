from uuid import UUID

from distributedinference.domain.agent import get_agent_attestation_use_case
from distributedinference.repository.agent_repository import AgentRepository
from distributedinference.repository.tee_orchestration_repository import (
    TeeOrchestrationRepository,
)
from distributedinference.service.agent_explorer.entities import (
    AgentAttestationResponse,
)


async def execute(
    agent_id: UUID,
    agent_repository: AgentRepository,
    tee_orchestration_repository: TeeOrchestrationRepository,
) -> AgentAttestationResponse:
    attestation = await get_agent_attestation_use_case.execute(
        agent_id,
        agent_repository,
        tee_orchestration_repository,
    )
    return AgentAttestationResponse(
        attestation=attestation,
    )
