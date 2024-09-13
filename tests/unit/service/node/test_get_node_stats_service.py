from datetime import datetime
from datetime import timezone
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from uuid_extensions import uuid7

from distributedinference.domain.node.entities import NodeStats
from distributedinference.domain.user.entities import User
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.repository.tokens_repository import UsageTokens
from distributedinference.service import error_responses
from distributedinference.service.node import get_node_stats_service as service
from distributedinference.service.node.entities import GetNodeStatsResponse
from distributedinference.service.node.entities import InferenceStats

NODE_UUID = UUID("40c95432-8b2c-4208-bdf4-84f49ff957a3")


def _get_user():
    return User(uid=uuid7(), name="John Doe", email="johndoe@mail.com")


async def test_execute_not_found():
    user = _get_user()

    mock_repository = AsyncMock(spec=NodeRepository)
    mock_repository.get_node_stats.return_value = None

    with pytest.raises(error_responses.NotFoundAPIError) as e:
        await service.execute(user, str(NODE_UUID), mock_repository, AsyncMock())
        assert e is not None


async def test_success():
    user = _get_user()
    created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)

    mock_repository = AsyncMock(spec=NodeRepository)
    node_stats = NodeStats(
        requests_served=12,
        average_time_to_first_token=0.34,
        benchmark_tokens_per_second=12.34,
        benchmark_model_name="model",
        benchmark_created_at=created_at,
    )
    mock_repository.get_node_stats.return_value = node_stats

    mock_tokens_repository = AsyncMock(spec=TokensRepository)
    usage_tokens = UsageTokens(
        consumer_user_profile_id=uuid7(),
        producer_node_info_id=NODE_UUID,
        model_name="model",
        prompt_tokens=1,
        completion_tokens=2,
        total_tokens=3,
        created_at=created_at,
    )
    mock_tokens_repository.get_user_latest_usage_tokens.return_value = [usage_tokens]
    mock_tokens_repository.get_latest_count_by_time_and_user.return_value = 321

    response = await service.execute(
        user, str(NODE_UUID), mock_repository, mock_tokens_repository
    )

    expected_response = GetNodeStatsResponse(
        requests_served=node_stats.requests_served,
        requests_served_day=321,
        average_time_to_first_token=node_stats.average_time_to_first_token,
        benchmark_tokens_per_second=node_stats.benchmark_tokens_per_second,
        benchmark_model_name=node_stats.benchmark_model_name,
        benchmark_created_at=node_stats.benchmark_created_at.timestamp(),
        completed_inferences=[
            InferenceStats(
                model_name=usage_tokens.model_name,
                prompt_tokens=usage_tokens.prompt_tokens,
                completion_tokens=usage_tokens.completion_tokens,
                total_tokens=usage_tokens.total_tokens,
                created_at=usage_tokens.created_at.timestamp(),
            )
        ],
    )
    assert response == expected_response
