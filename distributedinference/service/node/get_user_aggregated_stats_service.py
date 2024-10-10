from typing import Optional

from distributedinference.domain.node_stats.entities import UserAggregatedStats
from distributedinference.domain.user.entities import User
from distributedinference.repository.node_stats_repository import NodeStatsRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.service import error_responses
from distributedinference.service.node.entities import GetUserAggregatedStatsResponse


async def execute(
    user: User,
    repository: NodeStatsRepository,
    tokens_repository: TokensRepository,
) -> GetUserAggregatedStatsResponse:
    user_aggregated_stats: Optional[UserAggregatedStats] = (
        await repository.get_user_aggregated_stats(user.uid)
    )
    if not user_aggregated_stats:
        raise error_responses.NotFoundAPIError()

    return GetUserAggregatedStatsResponse(
        total_requests_served=user_aggregated_stats.total_requests_served,
        requests_served_day=await tokens_repository.get_latest_count_by_time_and_user(
            user.uid
        ),
        average_time_to_first_token=user_aggregated_stats.average_time_to_first_token,
        benchmark_total_tokens_per_second=user_aggregated_stats.benchmark_total_tokens_per_second,
    )
