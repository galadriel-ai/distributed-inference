from uuid import UUID
from distributedinference.repository.agent_repository import AgentRepository


async def execute(
    repository: AgentRepository,
    agent_id: UUID,
) -> None:
    await repository.delete_agent(agent_id)
