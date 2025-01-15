from uuid import UUID

from distributedinference.domain.agent.entities import AgentLog
from distributedinference.domain.agent.entities import AgentLogInput
from distributedinference.domain.agent.logs import add_agent_logs_use_case
from distributedinference.domain.user.entities import User
from distributedinference.repository.agent_logs_repository import AgentLogsRepository
from distributedinference.repository.agent_repository import AgentRepository
from distributedinference.service import error_responses
from distributedinference.service.agent.entities import AddLogsRequest
from distributedinference.service.agent.entities import AddLogsResponse

RATE_LIMIT_TIME_SECONDS = 60
MAX_COUNT_IN_TIME = 60


async def execute(
    agent_id: UUID,
    request: AddLogsRequest,
    user: User,
    agent_repository: AgentRepository,
    repository: AgentLogsRepository,
) -> AddLogsResponse:
    agent = await agent_repository.get_agent(agent_id)
    if not agent or agent.user_profile_id != user.uid:
        raise error_responses.NotFoundAPIError("Agent with given ID not found")

    # Basic rate-limiting, keep in mind that inserts happen in batches
    # meaning the count can be bigger than the amount of requests done
    count = await repository.get_count_by_agent(agent_id, RATE_LIMIT_TIME_SECONDS)
    if count > MAX_COUNT_IN_TIME:
        raise error_responses.RateLimitError({})

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
