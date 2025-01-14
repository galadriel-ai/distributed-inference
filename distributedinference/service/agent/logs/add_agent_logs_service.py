from uuid import UUID

from distributedinference.domain.agent.entities import AgentLog
from distributedinference.domain.agent.entities import AgentLogInput
from distributedinference.domain.agent.logs import add_agent_logs_use_case
from distributedinference.repository.agent_logs_repository import AgentLogsRepository
from distributedinference.repository.agent_repository import AgentRepository
from distributedinference.service import error_responses
from distributedinference.service.agent.entities import AddLogsRequest
from distributedinference.service.agent.entities import AddLogsResponse


async def execute(
    agent_id: UUID,
    request: AddLogsRequest,
    agent_repository: AgentRepository,
    repository: AgentLogsRepository,
) -> AddLogsResponse:
    # TODO: rate limits
    agent = await agent_repository.get_agent(agent_id)
    if not agent:
        raise error_responses.NotFoundAPIError("Agent with given ID not found")

    await add_agent_logs_use_case.execute(_format_input(agent_id, request), repository)

    return AddLogsResponse()


def _format_input(agent_id: UUID, request: AddLogsRequest) -> AgentLogInput:
    return AgentLogInput(
        agent_id=agent_id,
        logs=[
            AgentLog(
                text=log.text,
                timestamp=log.timestamp,
            )
            for log in request.logs
        ],
    )
