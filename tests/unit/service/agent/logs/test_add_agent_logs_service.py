from datetime import datetime
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from uuid_extensions import uuid7

from distributedinference.domain.agent.entities import Agent
from distributedinference.domain.agent.entities import AgentLog
from distributedinference.domain.agent.entities import AgentLogInput
from distributedinference.domain.user.entities import User
from distributedinference.service import error_responses
from distributedinference.service.agent.entities import AddLogsRequest
from distributedinference.service.agent.entities import Log
from distributedinference.service.agent.entities import SUPPORTED_LOG_LEVELS
from distributedinference.service.agent.logs import add_agent_logs_service as service

AGENT_ID = UUID("067865aa-8f86-7cb9-8000-f86624c51873")


def _get_request_input() -> AddLogsRequest:
    return AddLogsRequest(
        logs=[Log(text="text", level=SUPPORTED_LOG_LEVELS[0], timestamp=1)]
    )


def _get_user() -> User:
    return User(
        uid=uuid7(),
        name="mock_name",
        email="mock_email",
        usage_tier_id=UUID("06706644-2409-7efd-8000-3371c5d632d3"),
    )


async def test_success():
    service.add_agent_logs_use_case = AsyncMock()

    agent_repo = AsyncMock()
    user = _get_user()
    agent_repo.get_agent.return_value = Agent(
        id=uuid7(),
        name="name",
        created_at=datetime(2021, 1, 1),
        docker_image="docker_image",
        docker_image_hash="docker_image_hash",
        env_vars={},
        last_updated_at=datetime(2021, 1, 1),
        user_profile_id=user.uid,
    )

    repo = AsyncMock()
    repo.get_count_by_agent.return_value = 0
    await service.execute(
        AGENT_ID,
        _get_request_input(),
        user,
        agent_repo,
        repo,
    )
    service.add_agent_logs_use_case.execute.assert_called_once_with(
        AgentLogInput(
            agent_id=AGENT_ID,
            logs=[
                AgentLog(
                    text="text",
                    level=SUPPORTED_LOG_LEVELS[0],
                    timestamp=1,
                )
            ],
        ),
        repo,
    )


async def test_agent_not_found():
    service.add_agent_logs_use_case = AsyncMock()

    agent_repo = AsyncMock()
    agent_repo.get_agent.return_value = Agent(
        id=uuid7(),
        name="name",
        created_at=datetime(2021, 1, 1),
        docker_image="docker_image",
        docker_image_hash="docker_image_hash",
        env_vars={},
        last_updated_at=datetime(2021, 1, 1),
        user_profile_id=uuid7(),
    )

    agent_repo.get_agent.return_value = None
    repo = AsyncMock()
    with pytest.raises(error_responses.NotFoundAPIError) as e:
        await service.execute(
            AGENT_ID,
            _get_request_input(),
            _get_user(),
            agent_repo,
            repo,
        )
        assert e is not None
    service.add_agent_logs_use_case.execute.assert_not_called()


async def test_agent_user_invalid():
    service.add_agent_logs_use_case = AsyncMock()

    agent_repo = AsyncMock()
    agent_repo.get_agent.return_value = None
    repo = AsyncMock()
    with pytest.raises(error_responses.NotFoundAPIError) as e:
        await service.execute(
            AGENT_ID,
            _get_request_input(),
            _get_user(),
            agent_repo,
            repo,
        )
        assert e is not None
    service.add_agent_logs_use_case.execute.assert_not_called()


async def test_rate_limited():
    service.add_agent_logs_use_case = AsyncMock()

    agent_repo = AsyncMock()
    user = _get_user()
    agent_repo.get_agent.return_value = Agent(
        id=uuid7(),
        name="name",
        created_at=datetime(2021, 1, 1),
        docker_image="docker_image",
        docker_image_hash="docker_image_hash",
        env_vars={},
        last_updated_at=datetime(2021, 1, 1),
        user_profile_id=user.uid,
    )

    repo = AsyncMock()
    repo.get_count_by_agent.return_value = 100000000000
    with pytest.raises(error_responses.RateLimitError) as e:
        await service.execute(
            AGENT_ID,
            _get_request_input(),
            user,
            agent_repo,
            repo,
        )
        assert e is not None
    service.add_agent_logs_use_case.execute.assert_not_called()
