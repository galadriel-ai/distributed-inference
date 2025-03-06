from typing import List
from typing import Optional
from uuid import UUID

import sqlalchemy

from distributedinference.domain.agent.entities import DeployedAgent
from distributedinference.domain.agent.entities import ExplorerAgentInstance
from distributedinference.repository.connection import SessionProvider

SQL_GET_AGENTS = """
SELECT
    id,
    name,
    docker_image,
    created_at
FROM agents
ORDER BY id DESC
LIMIT :count;
"""

SQL_GET_AGENTS_COUNT = """
SELECT COUNT(id)
FROM agents;
"""

SQL_GET_AGENT_ID = """
SELECT
    id,
    name,
    docker_image,
    created_at
FROM agents
WHERE id = :agent_id;
"""

SQL_GET_AGENT_INSTANCES_BY_AGENT_ID = """
SELECT
    id,
    enclave_cid,
    is_deleted,
    created_at
FROM agent_instance
WHERE agent_id = :agent_id;
"""


class AgentExplorerRepository:

    def __init__(self, session_provider_read: SessionProvider):
        self._session_provider_read = session_provider_read

    async def get_latest_agents(self, count: int = 5) -> List[DeployedAgent]:
        data = {"count": count}
        results = []
        async with self._session_provider_read.get() as session:
            rows = await session.execute(sqlalchemy.text(SQL_GET_AGENTS), data)
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

    async def get_agents_count(self) -> int:
        async with self._session_provider_read.get() as session:
            result = await session.execute(sqlalchemy.text(SQL_GET_AGENTS_COUNT))
            return int(result.scalar() or 0)

    async def get_agent(self, agent_id: UUID) -> Optional[DeployedAgent]:
        data = {"agent_id": agent_id}
        async with self._session_provider_read.get() as session:
            result = await session.execute(sqlalchemy.text(SQL_GET_AGENT_ID), data)
            row = result.first()
            if row:
                return DeployedAgent(
                    id=row.id,
                    name=row.name,
                    docker_image=row.docker_image,
                    created_at=row.created_at,
                )
        return None

    async def get_agent_instances(self, agent_id: UUID) -> List[ExplorerAgentInstance]:
        data = {"agent_id": agent_id}
        results = []
        async with self._session_provider_read.get() as session:
            rows = await session.execute(
                sqlalchemy.text(SQL_GET_AGENT_INSTANCES_BY_AGENT_ID), data
            )
            for row in rows:
                results.append(
                    ExplorerAgentInstance(
                        id=row.id,
                        enclave_cid=row.enclave_cid,
                        is_deleted=row.is_deleted,
                        created_at=row.created_at,
                    )
                )
        return results
