from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from distributedinference.domain.agent.entities import AgentLog
from distributedinference.domain.agent.entities import AgentLogInput
from distributedinference.service import error_responses
from distributedinference.service.agent.entities import AddLogsRequest
from distributedinference.service.agent.entities import Log
from distributedinference.service.agent.logs import add_agent_logs_service as service

AGENT_ID = UUID("067865aa-8f86-7cb9-8000-f86624c51873")


def _get_request_input() -> AddLogsRequest:
    return AddLogsRequest(logs=[Log(text="text", timestamp=1)])


async def test_success():
    service.add_agent_logs_use_case = AsyncMock()

    agent_repo = AsyncMock()
    repo = AsyncMock()
    await service.execute(
        AGENT_ID,
        _get_request_input(),
        agent_repo,
        repo,
    )
    service.add_agent_logs_use_case.execute.assert_called_once_with(
        AgentLogInput(
            agent_id=AGENT_ID,
            logs=[
                AgentLog(
                    text="text",
                    timestamp=1,
                )
            ],
        ),
        repo,
    )


async def test_agent_not_found():
    service.add_agent_logs_use_case = AsyncMock()

    agent_repo = AsyncMock()
    agent_repo.get_agent.return_value = None
    repo = AsyncMock()
    with pytest.raises(error_responses.NotFoundAPIError) as e:
        await service.execute(
            AGENT_ID,
            _get_request_input(),
            agent_repo,
            repo,
        )
        assert e is not None
    service.add_agent_logs_use_case.execute.assert_not_called()
