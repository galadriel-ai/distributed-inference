from distributedinference.domain.agent.entities import GetAgentLogsInput
from distributedinference.domain.agent.entities import GetAgentLogsOutput
from distributedinference.repository.agent_logs_repository import AgentLogsRepository


async def execute(
    request: GetAgentLogsInput,
    repository: AgentLogsRepository,
) -> GetAgentLogsOutput:
    logs = await repository.get(request)
    return GetAgentLogsOutput(
        logs=logs, cursor=logs[-1].id if len(logs) == request.limit else None
    )
