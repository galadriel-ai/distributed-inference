from typing import Optional
from uuid import UUID

import sqlalchemy
from uuid_extensions import uuid7

from distributedinference import api_logger
from distributedinference.domain.node.entities import NodeBenchmark
from distributedinference.repository.connection import SessionProvider
from distributedinference.repository.utils import utcnow

logger = api_logger.get()

SQL_INSERT_OR_UPDATE_NODE_BENCHMARK = """
WITH node_exists AS (
    SELECT id
    FROM node_info
    WHERE id = :node_id
      AND user_profile_id = :user_profile_id
)
INSERT INTO node_benchmark (
    id,
    node_id,
    model_name,
    tokens_per_second,
    created_at,
    last_updated_at
) 
SELECT 
    :id, 
    ne.id, 
    :model_name, 
    :tokens_per_second, 
    :created_at, 
    :last_updated_at
FROM node_exists ne
ON CONFLICT (node_id, model_name) DO UPDATE SET
    tokens_per_second = EXCLUDED.tokens_per_second,
    last_updated_at = EXCLUDED.last_updated_at;
"""

SQL_GET_NODE_BENCHMARK = """
SELECT
    nb.id,
    nb.node_id,
    nb.model_name,
    nb.tokens_per_second,
    nb.created_at,
    nb.last_updated_at
FROM node_benchmark nb
LEFT JOIN node_info ni on nb.node_id = ni.id
WHERE 
    ni.id = :id
    AND ni.user_profile_id = :user_profile_id
    AND nb.model_name = :model_name;
"""


class BenchmarkRepository:

    def __init__(
        self, session_provider: SessionProvider
    ):
        self._session_provider = session_provider

    async def save_node_benchmark(
        self, user_profile_id: UUID, benchmark: NodeBenchmark
    ):
        data = {
            "id": str(uuid7()),
            "node_id": benchmark.node_id,
            "user_profile_id": user_profile_id,
            "model_name": benchmark.model_name,
            "tokens_per_second": benchmark.tokens_per_second,
            "created_at": utcnow(),
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            await session.execute(
                sqlalchemy.text(SQL_INSERT_OR_UPDATE_NODE_BENCHMARK), data
            )
            await session.commit()

    async def get_node_benchmark(
        self, user_id: UUID, node_id: UUID, model_name: str
    ) -> Optional[NodeBenchmark]:
        data = {"id": node_id, "user_profile_id": user_id, "model_name": model_name}
        async with self._session_provider.get() as session:
            result = await session.execute(
                sqlalchemy.text(SQL_GET_NODE_BENCHMARK), data
            )
            row = result.first()
            if row:
                return NodeBenchmark(
                    node_id=node_id,
                    model_name=row.model_name,
                    tokens_per_second=row.tokens_per_second,
                )
        return None
