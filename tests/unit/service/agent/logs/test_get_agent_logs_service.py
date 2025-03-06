from datetime import datetime
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from distributedinference.domain.agent.entities import Agent
from distributedinference.domain.agent.entities import AgentLogOutput
from distributedinference.domain.agent.entities import GetAgentLogsInput
from distributedinference.domain.agent.entities import GetAgentLogsOutput
from distributedinference.service import error_responses
from distributedinference.service.agent.entities import GetLogsRequest
from distributedinference.service.agent.entities import GetLogsResponse
from distributedinference.service.agent.entities import Log
from distributedinference.service.agent.entities import SUPPORTED_LOG_LEVELS
from distributedinference.service.agent.entities import SUPPORTED_LOG_LEVEL_STANDALONE
from distributedinference.service.agent.logs import get_agent_logs_service as service

USER_ID = UUID("067865bc-d577-7e80-8000-5e84dee08b75")
AGENT_ID = UUID("067865bc-dcdd-75f5-8000-570a418402c1")


def _get_request_input() -> GetLogsRequest:
    return GetLogsRequest(
        agent_id=AGENT_ID, limit=2, cursor=None, level=SUPPORTED_LOG_LEVELS[0]
    )


def _get_agent(user_uid: UUID) -> Agent:
    return Agent(
        id=user_uid,
        name="name",
        created_at=datetime(2020, 1, 1),
        docker_image="docker_image",
        docker_image_hash="docker_image_hash",
        env_vars={},
        last_updated_at=datetime(2020, 1, 2),
        user_profile_id=user_uid,
    )


async def test_success():
    service.get_agent_logs_use_case = AsyncMock()
    service.get_agent_logs_use_case.execute.return_value = GetAgentLogsOutput(
        logs=[
            AgentLogOutput(
                id=UUID("067865cf-f843-758a-8000-2690c3ead48a"),
                text="text",
                level=SUPPORTED_LOG_LEVELS[0],
                timestamp=2,
            )
        ],
        cursor=None,
    )

    agent_repo = AsyncMock()
    agent_repo.get_agent.return_value = _get_agent(USER_ID)
    repo = AsyncMock()
    result = await service.execute(
        _get_request_input(),
        agent_repo,
        repo,
    )
    assert result == GetLogsResponse(
        logs=[
            Log(
                text="text",
                level=SUPPORTED_LOG_LEVELS[0],
                timestamp=2,
            )
        ],
        cursor=None,
    )


async def test_agent_not_found():
    service.get_agent_logs_use_case = AsyncMock()

    agent_repo = AsyncMock()
    agent_repo.get_agent.return_value = None
    repo = AsyncMock()
    with pytest.raises(error_responses.NotFoundAPIError) as e:
        await service.execute(
            _get_request_input(),
            agent_repo,
            repo,
        )
        assert e is not None
    service.get_agent_logs_use_case.execute.assert_not_called()


async def test_uses_correct_levels():
    service.get_agent_logs_use_case = AsyncMock()
    service.get_agent_logs_use_case.execute.return_value = GetAgentLogsOutput(
        logs=[
            AgentLogOutput(
                id=UUID("067865cf-f843-758a-8000-2690c3ead48a"),
                text="text",
                level=SUPPORTED_LOG_LEVELS[1],
                timestamp=2,
            )
        ],
        cursor=None,
    )

    agent_repo = AsyncMock()
    agent_repo.get_agent.return_value = _get_agent(USER_ID)
    repo = AsyncMock()
    request_input = _get_request_input()
    request_input.level = SUPPORTED_LOG_LEVELS[1]

    await service.execute(
        request_input,
        agent_repo,
        repo,
    )
    service.get_agent_logs_use_case.execute.assert_called_with(
        GetAgentLogsInput(
            agent_id=UUID("067865bc-dcdd-75f5-8000-570a418402c1"),
            limit=2,
            levels=SUPPORTED_LOG_LEVELS[1:-1],
            cursor=None,
        ),
        repo,
    )


async def test_queries_thoughts_only():
    service.get_agent_logs_use_case = AsyncMock()
    service.get_agent_logs_use_case.execute.return_value = GetAgentLogsOutput(
        logs=[
            AgentLogOutput(
                id=UUID("067865cf-f843-758a-8000-2690c3ead48a"),
                text="text",
                level=SUPPORTED_LOG_LEVEL_STANDALONE,
                timestamp=2,
            )
        ],
        cursor=None,
    )

    agent_repo = AsyncMock()
    agent_repo.get_agent.return_value = _get_agent(USER_ID)
    repo = AsyncMock()
    request_input = _get_request_input()
    request_input.level = SUPPORTED_LOG_LEVEL_STANDALONE

    await service.execute(
        request_input,
        agent_repo,
        repo,
    )
    service.get_agent_logs_use_case.execute.assert_called_with(
        GetAgentLogsInput(
            agent_id=UUID("067865bc-dcdd-75f5-8000-570a418402c1"),
            limit=2,
            levels=[SUPPORTED_LOG_LEVEL_STANDALONE],
            cursor=None,
        ),
        repo,
    )
