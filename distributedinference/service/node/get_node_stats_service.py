from typing import List
from typing import Optional

from distributedinference.domain.node.entities import NodeInfo
from distributedinference.domain.node.entities import NodeStats
from distributedinference.domain.user.entities import User
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.repository.tokens_repository import UsageTokens
from distributedinference.service import error_responses
from distributedinference.service.node.entities import GetNodeStatsResponse
from distributedinference.service.node.entities import InferenceStats

INFERENCES_COUNT = 10


async def execute(
    user: User,
    node_info: NodeInfo,
    repository: NodeRepository,
    tokens_repository: TokensRepository,
) -> GetNodeStatsResponse:
    node_stats: Optional[NodeStats] = await repository.get_node_stats(
        user.uid, node_info.node_id
    )
    if not node_stats:
        raise error_responses.NotFoundAPIError()
    average_time_to_first_token = None
    if node_stats.average_time_to_first_token:
        average_time_to_first_token = node_stats.average_time_to_first_token

    usage_tokens = await tokens_repository.get_user_latest_usage_tokens(
        user.uid, node_info.node_id, INFERENCES_COUNT
    )

    return GetNodeStatsResponse(
        requests_served=node_stats.requests_served,
        requests_served_day=await tokens_repository.get_latest_count_by_time_and_node(
            node_info.node_id
        ),
        average_time_to_first_token=average_time_to_first_token,
        benchmark_tokens_per_second=node_stats.benchmark_tokens_per_second,
        benchmark_model_name=node_stats.benchmark_model_name,
        benchmark_created_at=(
            None
            if not node_stats.benchmark_created_at
            else int(node_stats.benchmark_created_at.timestamp())
        ),
        completed_inferences=_get_completed_inferences(usage_tokens),
    )


def _get_completed_inferences(usage_tokens: List[UsageTokens]) -> List[InferenceStats]:
    return [
        InferenceStats(
            model_name=i.model_name,
            prompt_tokens=i.prompt_tokens,
            completion_tokens=i.completion_tokens,
            total_tokens=i.total_tokens,
            created_at=int(i.created_at.timestamp()),
        )
        for i in usage_tokens
    ]
