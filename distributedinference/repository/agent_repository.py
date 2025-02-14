import json
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from uuid import UUID

import sqlalchemy
from uuid_extensions import uuid7

from distributedinference.domain.agent.entities import Agent
from distributedinference.domain.agent.entities import AgentInstance
from distributedinference.repository.connection import SessionProvider
from distributedinference.repository.utils import utcnow

# pylint: disable=R0801
SQL_INSERT_AGENT = """
INSERT INTO agents (
    id,
    name,
    user_profile_id,
    docker_image,
    docker_image_hash,
    env_vars,
    is_deleted,
    created_at,
    last_updated_at
) VALUES (
    :id,
    :name,
    :user_profile_id,
    :docker_image,
    :docker_image_hash,
    :env_vars,
    FALSE,
    :created_at,
    :last_updated_at
);
"""

SQL_INSERT_AGENT_VERSION = """
INSERT INTO agent_version (
    id,
    agent_id,
    docker_image,
    docker_image_hash,
    env_vars,
    created_at,
    last_updated_at
) VALUES (
    :id,
    :agent_id,
    :docker_image,
    :docker_image_hash,
    :env_vars,
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
    docker_image_hash,
    env_vars,
    created_at,
    last_updated_at
FROM agents
WHERE id = :id AND (is_deleted = :is_deleted OR :is_deleted IS NULL);
"""

SQL_GET_ALL_AGENTS = """
SELECT
    id,
    name,
    user_profile_id,
    docker_image,
    docker_image_hash,
    env_vars,
    created_at,
    last_updated_at
FROM agents;
"""

SQL_GET_USER_AGENTS = """
SELECT
    id,
    name,
    user_profile_id,
    docker_image,
    docker_image_hash,
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
    docker_image = COALESCE(:docker_image, docker_image),
    docker_image_hash = COALESCE(:docker_image_hash, docker_image_hash),
    env_vars = :env_vars,
    last_updated_at = :last_updated_at
WHERE id = :id AND is_deleted = FALSE;
"""

SQL_DELETE_AGENT = """
UPDATE agents
SET is_deleted = true
WHERE id = :id;
"""

# pylint: disable=R0801
SQL_INSERT_AGENT_INSTANCE = """
INSERT INTO agent_instance (
    id,
    agent_id,
    enclave_cid,
    is_deleted,
    created_at,
    last_updated_at
) VALUES (
    :id,
    :agent_id,
    :enclave_cid,
    FALSE,
    :created_at,
    :last_updated_at
);
"""

SQL_GET_AGENT_INSTANCES = """
SELECT
    id,
    agent_id,
    enclave_cid,
    is_deleted,
    created_at,
    last_updated_at
FROM agent_instance;
"""

SQL_GET_AGENT_INSTANCE_BY_AGENT_ID = """
SELECT
    id,
    agent_id,
    enclave_cid,
    is_deleted,
    created_at,
    last_updated_at
FROM agent_instance
WHERE agent_id = :agent_id AND is_deleted = FALSE;
"""

SQL_DELETE_AGENT_INSTANCE = """
UPDATE agent_instance
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
        self, user_id: UUID, name: str, docker_image: str, docker_image_hash: str, env_vars: Dict[str, Any]
    ) -> UUID:
        agent_id = uuid7()
        data = {
            "id": agent_id,
            "name": name,
            "user_profile_id": user_id,
            "docker_image": docker_image,
            "docker_image_hash": docker_image_hash,
            "env_vars": json.dumps(env_vars),
            "created_at": utcnow(),
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_INSERT_AGENT), data)
            await session.commit()
            return agent_id
        
    async def insert_agent_version(
        self, agent_id: UUID, docker_image: str, docker_image_hash: str, env_vars: Dict[str, Any]
    ) -> UUID:
        agent_version_id = uuid7()
        data = {
            "id": agent_version_id,
            "agent_id": agent_id,
            "docker_image": docker_image,
            "docker_image_hash": docker_image_hash,
            "env_vars": json.dumps(env_vars),
            "created_at": utcnow(),
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_INSERT_AGENT_VERSION), data)
            await session.commit()
            return agent_version_id

    async def get_agent(
        self, agent_id: UUID, is_deleted: Optional[bool] = False
    ) -> Optional[Agent]:
        data = {"id": agent_id, "is_deleted": is_deleted}
        async with self._session_provider_read.get() as session:
            result = await session.execute(sqlalchemy.text(SQL_GET_AGENT_BY_ID), data)
            row = result.first()
            if row:
                return Agent(
                    id=row.id,
                    name=row.name,
                    user_profile_id=row.user_profile_id,
                    docker_image=row.docker_image,
                    docker_image_hash=row.docker_image_hash,
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
                        id=row.id,
                        name=row.name,
                        user_profile_id=row.user_profile_id,
                        docker_image=row.docker_image,
                        docker_image_hash=row.docker_image_hash,
                        env_vars=row.env_vars,
                        created_at=row.created_at,
                        last_updated_at=row.last_updated_at,
                    )
                )
        return results

    async def get_all_agents(self) -> List[Agent]:
        results = []
        async with self._session_provider_read.get() as session:
            rows = await session.execute(sqlalchemy.text(SQL_GET_ALL_AGENTS))
            for row in rows:
                results.append(
                    Agent(
                        id=row.id,
                        name=row.name,
                        user_profile_id=row.user_profile_id,
                        docker_image=row.docker_image,
                        docker_image_hash=row.docker_image_hash,
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
        docker_image_hash: Optional[str],
        env_vars: Dict[str, Any],
    ) -> None:
        data = {
            "id": agent_id,
            "name": name,
            "docker_image": docker_image,
            "docker_image_hash": docker_image_hash,
            "env_vars": json.dumps(env_vars),
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_UPDATE_AGENT), data)
            await session.commit()

    async def delete_agent(self, agent_id: UUID) -> None:
        data = {"id": agent_id}
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_DELETE_AGENT), data)
            await session.commit()

    async def insert_agent_instance(
        self, agent_id: UUID, agent_instance_id: UUID, enclave_cid: str
    ) -> UUID:
        data = {
            "id": agent_instance_id,
            "agent_id": agent_id,
            "enclave_cid": enclave_cid,
            "created_at": utcnow(),
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_INSERT_AGENT_INSTANCE), data)
            await session.commit()
            return agent_instance_id

    async def get_agent_instances(self) -> List[AgentInstance]:
        results = []
        async with self._session_provider_read.get() as session:
            rows = await session.execute(sqlalchemy.text(SQL_GET_AGENT_INSTANCES))
            for row in rows:
                results.append(
                    AgentInstance(
                        id=row.id,
                        agent_id=row.id,
                        enclave_cid=row.enclave_cid,
                        created_at=row.created_at,
                        last_updated_at=row.last_updated_at,
                    )
                )
        return results

    async def get_agent_instance(self, agent_id: UUID) -> Optional[AgentInstance]:
        data = {"agent_id": agent_id}
        async with self._session_provider_read.get() as session:
            result = await session.execute(
                sqlalchemy.text(SQL_GET_AGENT_INSTANCE_BY_AGENT_ID), data
            )
            row = result.first()
            if row:
                return AgentInstance(
                    id=row.id,
                    agent_id=row.id,
                    enclave_cid=row.enclave_cid,
                    created_at=row.created_at,
                    last_updated_at=row.last_updated_at,
                )
        return None

    async def delete_agent_instance(self, agent_instance_id: UUID) -> None:
        data = {"id": agent_instance_id}
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_DELETE_AGENT_INSTANCE), data)
            await session.commit()
