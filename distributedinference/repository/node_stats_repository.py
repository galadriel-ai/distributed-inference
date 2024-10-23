from typing import Optional
from uuid import UUID

import sqlalchemy

from distributedinference import api_logger
from distributedinference.domain.node_stats.entities import UserAggregatedStats
from distributedinference.domain.node_stats.entities import NodeStats
from distributedinference.repository import utils
from distributedinference.repository.connection import SessionProvider
from distributedinference.utils.timer import async_timer

SQL_GET_NODE_STATS = """
SELECT
    nm.requests_served,
    nm.time_to_first_token,
    nb.tokens_per_second AS benchmark_tokens_per_second,
    nb.model_name AS benchmark_model_name,
    nb.created_at AS benchmark_created_at
FROM node_info ni
LEFT JOIN node_metrics nm on nm.node_info_id = ni.id
LEFT JOIN node_benchmark nb on ni.id = nb.node_id
WHERE ni.user_profile_id = :user_profile_id AND ni.id = :id
LIMIT 1;
"""

SQL_GET_USER_STATS = """
SELECT
    SUM(nm.requests_served) AS total_requests_served,
    AVG(nm.time_to_first_token) AS average_time_to_first_token,
    SUM(nb.tokens_per_second) AS benchmark_total_tokens_per_second
FROM node_info ni
LEFT JOIN node_metrics nm on nm.node_info_id = ni.id
LEFT JOIN node_benchmark nb on ni.id = nb.node_id
WHERE ni.user_profile_id = :user_profile_id;
"""

logger = api_logger.get()


class NodeStatsRepository:

    def __init__(
        self, session_provider: SessionProvider, session_provider_read: SessionProvider
    ):
        self._session_provider = session_provider
        self._session_provider_read = session_provider_read

    @async_timer("node_stats_repository.get_node_stats", logger=logger)
    async def get_node_stats(self, user_id: UUID, node_id: UUID) -> Optional[NodeStats]:
        data = {"id": node_id, "user_profile_id": user_id}
        async with self._session_provider_read.get() as session:
            result = await session.execute(sqlalchemy.text(SQL_GET_NODE_STATS), data)
            row = result.first()
            if row:
                return NodeStats(
                    requests_served=utils.parse_int(row.requests_served),
                    average_time_to_first_token=utils.parse_float(
                        row.time_to_first_token
                    ),
                    benchmark_tokens_per_second=utils.parse_float(
                        row.benchmark_tokens_per_second
                    ),
                    benchmark_model_name=row.benchmark_model_name,
                    benchmark_created_at=row.benchmark_created_at,
                )
        return None

    @async_timer("node_stats_repository.get_user_aggregated_stats", logger=logger)
    async def get_user_aggregated_stats(
        self, user_id: UUID
    ) -> Optional[UserAggregatedStats]:
        data = {"user_profile_id": user_id}
        async with self._session_provider_read.get() as session:
            result = await session.execute(sqlalchemy.text(SQL_GET_USER_STATS), data)
            row = result.first()
            if row:
                return UserAggregatedStats(
                    total_requests_served=row.total_requests_served,
                    average_time_to_first_token=row.average_time_to_first_token,
                    benchmark_total_tokens_per_second=row.benchmark_total_tokens_per_second,
                )
        return None
