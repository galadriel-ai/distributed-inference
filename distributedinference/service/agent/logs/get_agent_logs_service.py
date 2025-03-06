from typing import List
from typing import Optional

from distributedinference.domain.agent.entities import GetAgentLogsInput
from distributedinference.domain.agent.logs import get_agent_logs_use_case
from distributedinference.repository.agent_logs_repository import AgentLogsRepository
from distributedinference.repository.agent_repository import AgentRepository
from distributedinference.service import error_responses
from distributedinference.service.agent.entities import GetLogsRequest
from distributedinference.service.agent.entities import GetLogsResponse
from distributedinference.service.agent.entities import Log
from distributedinference.service.agent.entities import SUPPORTED_LOG_LEVELS
from distributedinference.service.agent.entities import SUPPORTED_LOG_LEVELS_TYPE
from distributedinference.service.agent.entities import SUPPORTED_LOG_LEVEL_STANDALONE

DEFAULT_LIMIT = 50


async def execute(
    request: GetLogsRequest,
    agent_repository: AgentRepository,
    repository: AgentLogsRepository,
) -> GetLogsResponse:
    agent = await agent_repository.get_agent(request.agent_id, is_deleted=None)
    if not agent:
        raise error_responses.NotFoundAPIError("Agent with given agent_id not found")

    response = await get_agent_logs_use_case.execute(
        GetAgentLogsInput(
            agent_id=request.agent_id,
            limit=request.limit or DEFAULT_LIMIT,
            levels=_get_request_log_levels(request.level),
            cursor=request.cursor,
        ),
        repository,
    )

    return GetLogsResponse(
        logs=[
            Log(
                text=log.text,
                level=log.level,
                timestamp=log.timestamp,
            )
            for log in response.logs
        ],
        cursor=response.cursor,
    )


def _get_request_log_levels(level: Optional[SUPPORTED_LOG_LEVELS_TYPE]) -> List[str]:
    if not level:
        level = SUPPORTED_LOG_LEVELS[0]
    if level == SUPPORTED_LOG_LEVEL_STANDALONE:
        return [SUPPORTED_LOG_LEVEL_STANDALONE]
    is_matched = False
    levels: List[str] = []
    for supported_level in SUPPORTED_LOG_LEVELS:
        if supported_level == SUPPORTED_LOG_LEVEL_STANDALONE:
            continue
        if supported_level == level:
            is_matched = True
        if is_matched:
            levels.append(supported_level)
    return levels
