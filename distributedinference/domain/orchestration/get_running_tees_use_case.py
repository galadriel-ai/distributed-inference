from typing import List

from distributedinference.domain.orchestration.entities import TEE
from distributedinference.repository.tee_orchestration_repository import (
    TeeOrchestrationRepository,
)


async def execute(repository: TeeOrchestrationRepository) -> List[TEE]:
    return await repository.get_all_tees()
