from distributedinference.domain.agent.entities import AgentLogInput
from distributedinference.repository.agent_logs_repository import AgentLogsRepository


async def execute(
    agent_logs: AgentLogInput,
    repository: AgentLogsRepository,
):
    await repository.add(agent_logs)
