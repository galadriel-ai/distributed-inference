from distributedinference.domain.agent.entities import Agent
from distributedinference.domain.orchestration.entities import TEE
from distributedinference.repository.tee_orchestration_repository import (
    TeeOrchestrationRepository,
)


async def execute(repository: TeeOrchestrationRepository, agent: Agent) -> None:
    # TODO
    pass
