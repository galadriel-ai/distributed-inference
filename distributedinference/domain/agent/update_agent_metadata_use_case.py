from uuid import UUID

from distributedinference.domain.agent.entities import UpdateAgentMetadataInput
from distributedinference.repository.agent_repository import AgentRepository


async def execute(
    agent_id: UUID,
    metadata_input: UpdateAgentMetadataInput,
    repository: AgentRepository,
) -> None:
    await repository.update_metadata(
        agent_id=agent_id, metadata=metadata_input.__dict__
    )
