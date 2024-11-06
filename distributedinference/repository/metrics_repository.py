from dataclasses import dataclass
from typing import List

import sqlalchemy

from distributedinference import api_logger
from distributedinference.domain.node.entities import NodeStatus
from distributedinference.repository.connection import SessionProvider
from distributedinference.utils.timer import async_timer

logger = api_logger.get()

SQL_GET_ALL_NODE_STATUSES = """
SELECT status, model_name, COUNT(*) AS status_model_count
FROM node_metrics
GROUP BY status, model_name;
"""


@dataclass
class NodeStatusesByModel:
    status: NodeStatus
    model_name: str
    count: int


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
