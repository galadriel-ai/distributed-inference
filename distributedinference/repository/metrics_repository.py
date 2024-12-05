from dataclasses import dataclass
from typing import List
from typing import Optional
from uuid import UUID

import sqlalchemy

from distributedinference import api_logger
from distributedinference.domain.node.entities import NodeBenchmark
from distributedinference.domain.node.entities import NodeStatus
from distributedinference.repository.connection import SessionProvider
from distributedinference.repository.tokens_repository import TotalTokensResponse
from distributedinference.utils.timer import async_timer

logger = api_logger.get()

SQL_GET_ALL_NODE_STATUSES = """
SELECT status, model_name, COUNT(*) AS status_model_count
FROM node_metrics
GROUP BY status, model_name;
"""

SQL_GET_CONNECTED_NODES = """
SELECT
    ni.id,
    ni.name,
    ni.gpu_model,
    ni.gpu_count,
    nb.model_name,
    nb.tokens_per_second AS benchmark_tokens_per_second
FROM node_info ni
LEFT JOIN node_metrics nm on ni.id = nm.node_info_id
LEFT JOIN node_benchmark nb on ni.id = nb.node_id AND nm.model_name = nb.model_name
WHERE nm.status::text LIKE 'RUNNING%';
"""

SQL_GET_ALL_NODE_TOTAL_TOKENS = """
SELECT
    producer_node_info_id,
    model_name,
    SUM(total_tokens) AS total_tokens,
    MAX(id) AS max_id
FROM usage_tokens
WHERE (:last_id IS NULL OR id > :last_id)
GROUP BY producer_node_info_id, model_name;
"""


@dataclass
class NodeStatusesByModel:
    status: NodeStatus
    model_name: str
    count: int


@dataclass
class NodeModelTotalTokens:
    model_name: str
    node_uid: UUID
    total_tokens: int


class MetricsRepository:

    def __init__(
        self, session_provider: SessionProvider, session_provider_read: SessionProvider
    ):
        self._session_provider = session_provider
        self._session_provider_read = session_provider_read

    @async_timer("metrics_repository.get_node_statuses", logger=logger)
    async def get_node_statuses(self) -> List[NodeStatusesByModel]:
        result = []
        async with self._session_provider_read.get() as session:
            rows = await session.execute(sqlalchemy.text(SQL_GET_ALL_NODE_STATUSES))
            for row in rows:
                result.append(
                    NodeStatusesByModel(
                        status=NodeStatus(row.status),
                        model_name=row.model_name,
                        count=row.status_model_count,
                    )
                )
        return result

    @async_timer("metrics_repository.get_connected_node_benchmarks", logger=logger)
    async def get_connected_node_benchmarks(self) -> List[NodeBenchmark]:
        async with self._session_provider_read.get() as session:
            rows = await session.execute(sqlalchemy.text(SQL_GET_CONNECTED_NODES))
            return [
                NodeBenchmark(
                    node_id=row.id,
                    model_name=row.model_name,
                    benchmark_tokens_per_second=row.benchmark_tokens_per_second,
                    gpu_model=row.gpu_model,
                    gpu_count=row.gpu_count,
                )
                for row in rows
            ]

    @async_timer("metrics_repository.get_all_nodes_total_tokens", logger=logger)
    async def get_all_nodes_total_tokens(
        self, start_from_id: Optional[UUID] = None
    ) -> TotalTokensResponse:
        tokens = []
        data = {
            "last_id": start_from_id,
        }
        async with self._session_provider_read.get() as session:
            rows = await session.execute(
                sqlalchemy.text(SQL_GET_ALL_NODE_TOTAL_TOKENS), data
            )
            for row in rows:
                tokens.append(
                    NodeModelTotalTokens(
                        node_uid=row.producer_node_info_id,
                        model_name=row.model_name,
                        total_tokens=row.total_tokens,
                    )
                )
                if max_id is None or row.max_id > max_id:
                    max_id = row.max_id
        return TotalTokensResponse(usage=tokens, last_id=max_id)
