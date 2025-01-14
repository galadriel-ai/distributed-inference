from distributedinference.domain.agent.entities import GetAgentLogsInput
from distributedinference.domain.agent.logs import get_agent_logs_use_case
from distributedinference.domain.user.entities import User
from distributedinference.repository.agent_logs_repository import AgentLogsRepository
from distributedinference.repository.agent_repository import AgentRepository
from distributedinference.service import error_responses
from distributedinference.service.agent.entities import GetLogsRequest
from distributedinference.service.agent.entities import GetLogsResponse
from distributedinference.service.agent.entities import Log

DEFAULT_LIMIT = 50


async def execute(
    request: GetLogsRequest,
    user: User,
    agent_repository: AgentRepository,
    repository: AgentLogsRepository,
) -> GetLogsResponse:
    agent = await agent_repository.get_agent(request.agent_id, is_deleted=None)
    if not agent or agent.user_profile_id != user.uid:
        raise error_responses.NotFoundAPIError("Agent with given agent_id not found")

    response = await get_agent_logs_use_case.execute(
        GetAgentLogsInput(
            agent_id=request.agent_id,
            limit=request.limit or DEFAULT_LIMIT,
            cursor=request.cursor,
        ),
        repository,
    )

    return GetLogsResponse(
        logs=[
            Log(
                text=log.text,
                timestamp=log.timestamp,
            )
            for log in response.logs
        ],
        cursor=response.cursor,
    )
