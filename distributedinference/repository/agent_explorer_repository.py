from typing import List

import sqlalchemy

from distributedinference.domain.agent.entities import DeployedAgent
from distributedinference.repository.connection import SessionProvider

SQL_GET_AGENT_INSTANCES = """
SELECT
    ai.id,
    a.name,
    a.docker_image,
    ai.created_at
FROM agent_instance ai
LEFT JOIN agents a on ai.agent_id = a.id
WHERE ai.is_deleted IS FALSE
LIMIT :count;
"""

SQL_GET_AGENT_INSTANCES_COUNT = """
SELECT COUNT(id)
FROM agent_instance
WHERE is_deleted IS FALSE;
"""


class AgentExplorerRepository:

    def __init__(self, session_provider_read: SessionProvider):
        self._session_provider_read = session_provider_read

    async def get_latest_deployed_agents(self, count: int = 5) -> List[DeployedAgent]:
        data = {"count": count}
        results = []
        async with self._session_provider_read.get() as session:
            rows = await session.execute(sqlalchemy.text(SQL_GET_AGENT_INSTANCES), data)
            for row in rows:
                results.append(
                    DeployedAgent(
                        id=row.id,
                        name=row.name,
                        docker_image=row.docker_image,
                        created_at=row.created_at,
                    )
                )
        return results

    async def get_agent_instances_count(self) -> int:
        async with self._session_provider_read.get() as session:
            result = await session.execute(
                sqlalchemy.text(SQL_GET_AGENT_INSTANCES_COUNT)
            )
            return int(result.scalar() or 0)
