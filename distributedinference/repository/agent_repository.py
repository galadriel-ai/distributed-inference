import json
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from uuid import UUID

import sqlalchemy
from uuid_extensions import uuid7

from distributedinference.domain.agent.entities import Agent
from distributedinference.repository.connection import SessionProvider
from distributedinference.repository.utils import utcnow


# pylint: disable=R0801
SQL_INSERT_AGENT = """
INSERT INTO agents (
    id,
    name,
    user_profile_id,
    docker_image,
    env_vars,
    is_deleted,
    created_at,
    last_updated_at
) VALUES (
    :id,
    :name,
    :user_profile_id,
    :docker_image,
    :env_vars,
    FALSE,
    :created_at,
    :last_updated_at
);
"""

SQL_GET_AGENT_BY_ID = """
SELECT
    id,
    name,
    user_profile_id,
    docker_image,
    env_vars,
    created_at,
    last_updated_at
FROM agents
WHERE id = :id AND is_deleted = FALSE;
"""

SQL_GET_USER_AGENTS = """
SELECT
    id,
    name,
    user_profile_id,
    docker_image,
    env_vars,
    created_at,
    last_updated_at
FROM agents
WHERE user_profile_id = :user_profile_id AND is_deleted = FALSE;
"""

SQL_UPDATE_AGENT = """
UPDATE 
    agents
SET 
    name = :name, 
    docker_image = :docker_image,
    env_vars = :env_vars,
    last_updated_at = :last_updated_at
WHERE id = :id AND is_deleted = FALSE;
"""

SQL_DELETE_AGENT = """
UPDATE agents
SET is_deleted = true
WHERE id = :id;
"""


class AgentRepository:

    def __init__(
        self, session_provider: SessionProvider, session_provider_read: SessionProvider
    ):
        self._session_provider = session_provider
        self._session_provider_read = session_provider_read

    async def insert_agent(
        self, user_id: UUID, name: str, docker_image: str, env_vars: Dict[str, Any]
    ) -> UUID:
        agent_id = uuid7()
        data = {
            "id": agent_id,
            "name": name,
            "user_profile_id": user_id,
            "docker_image": docker_image,
            "env_vars": json.dumps(env_vars),
            "created_at": utcnow(),
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_INSERT_AGENT), data)
            await session.commit()
            return agent_id

    async def get_agent(self, agent_id: UUID) -> Optional[Agent]:
        data = {"id": agent_id}
        async with self._session_provider_read.get() as session:
            result = await session.execute(sqlalchemy.text(SQL_GET_AGENT_BY_ID), data)
            row = result.first()
            if row:
                return Agent(
                    agent_id=row.id,
                    name=row.name,
                    user_profile_id=row.user_profile_id,
                    docker_image=row.docker_image,
                    env_vars=row.env_vars,
                    created_at=row.created_at,
                    last_updated_at=row.last_updated_at,
                )
        return None

    async def get_user_agents(self, user_profile_id: UUID) -> List[Agent]:
        data = {"user_profile_id": user_profile_id}
        results = []
        async with self._session_provider_read.get() as session:
            rows = await session.execute(sqlalchemy.text(SQL_GET_USER_AGENTS), data)
            for row in rows:
                results.append(
                    Agent(
                        agent_id=row.id,
                        name=row.name,
                        user_profile_id=row.user_profile_id,
                        docker_image=row.docker_image,
                        env_vars=row.env_vars,
                        created_at=row.created_at,
                        last_updated_at=row.last_updated_at,
                    )
                )
        return results

    async def update_agent(
        self,
        agent_id: UUID,
        name: str,
        docker_image: Optional[str],
        env_vars: Dict[str, Any],
    ) -> None:
        data = {
            "id": agent_id,
            "name": name,
            "docker_image": docker_image,
            "env_vars": json.dumps(env_vars),
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            result = await session.execute(sqlalchemy.text(SQL_UPDATE_AGENT), data)
            await session.commit()
            print(result)

    async def delete_agent(self, agent_id: UUID) -> None:
        data = {"id": agent_id}
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_DELETE_AGENT), data)
            await session.commit()
