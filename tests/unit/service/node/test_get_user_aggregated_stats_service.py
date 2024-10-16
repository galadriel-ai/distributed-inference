from unittest.mock import AsyncMock

import pytest
from uuid import UUID
from uuid_extensions import uuid7

from distributedinference.domain.node_stats.entities import UserAggregatedStats
from distributedinference.domain.user.entities import User
from distributedinference.repository.node_stats_repository import NodeStatsRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.service import error_responses
from distributedinference.service.node import (
    get_user_aggregated_stats_service as service,
)
from distributedinference.service.node.entities import GetUserAggregatedStatsResponse


def _get_user():
    return User(
        uid=uuid7(),
        name="aggregated",
        email="johndoe@mail.com",
        usage_tier_id=UUID("06706644-2409-7efd-8000-3371c5d632d3"),
    )


async def test_not_found():
    user = _get_user()

    mock_repository = AsyncMock(spec=NodeStatsRepository)
    mock_repository.get_user_aggregated_stats.return_value = None

    # Not even sure this is possible though
    with pytest.raises(error_responses.NotFoundAPIError) as e:
        await service.execute(user, mock_repository, AsyncMock())
        assert e is not None


async def test_success():
    user = _get_user()

    mock_repository = AsyncMock(spec=NodeStatsRepository)
    aggregated_stats = UserAggregatedStats(
        total_requests_served=12,
        average_time_to_first_token=1.23,
        benchmark_total_tokens_per_second=123.23,
    )
    mock_repository.get_user_aggregated_stats.return_value = aggregated_stats

    mock_tokens_repository = AsyncMock(spec=TokensRepository)
    mock_tokens_repository.get_latest_count_by_time_and_user.return_value = 13

    response = await service.execute(user, mock_repository, mock_tokens_repository)
    expected_response = GetUserAggregatedStatsResponse(
        total_requests_served=aggregated_stats.total_requests_served,
        requests_served_day=13,
        average_time_to_first_token=aggregated_stats.average_time_to_first_token,
        benchmark_total_tokens_per_second=aggregated_stats.benchmark_total_tokens_per_second,
    )
    assert response == expected_response
