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
from distributedinference.domain.agent.entities import Attestation
from distributedinference.domain.agent.entities import AttestationDetails
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
    tee_host_base_url,
    enclave_cid,
    instance_env_vars,
    is_deleted,
    created_at,
    last_updated_at
) VALUES (
    :id,
    :agent_id,
    :tee_host_base_url,
    :enclave_cid,
    :instance_env_vars,
    FALSE,
    :created_at,
    :last_updated_at
);
"""

SQL_GET_AGENT_INSTANCES = """
SELECT
    id,
    agent_id,
    tee_host_base_url,
    enclave_cid,
    instance_env_vars,
    is_deleted,
    pcr0,
    created_at,
    last_updated_at
FROM agent_instance
WHERE (is_deleted = :is_deleted OR :is_deleted IS NULL);
"""

SQL_GET_AGENT_INSTANCE_BY_AGENT_ID = """
SELECT
    id,
    agent_id,
    tee_host_base_url,
    enclave_cid,
    instance_env_vars,
    is_deleted,
    pcr0,
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

SQL_UPDATE_PCR0 = """
UPDATE agent_instance
SET 
    pcr0 = :pcr0,
    last_updated_at = :last_updated_at
WHERE id = :id;
"""

SQL_INSERT_ATTESTATION = """
INSERT INTO agent_attestation (
    id, 
    agent_instance_id, 
    attestation, 
    valid_from, 
    valid_to, 
    created_at, 
    last_updated_at
) VALUES (
    :id, 
    :agent_instance_id, 
    :attestation, 
    :valid_from, 
    :valid_to, 
    :created_at, 
    :last_updated_at
);
"""

SQL_GET_ATTESTATIONS_BY_AGENT_INSTANCE_ID = """
SELECT
    id,
    agent_instance_id,
    attestation,
    valid_from,
    valid_to,
    created_at,
    last_updated_at
FROM agent_attestation
WHERE agent_instance_id = :agent_instance_id
ORDER BY id;
"""


class AgentRepository:

    def __init__(
        self, session_provider: SessionProvider, session_provider_read: SessionProvider
    ):
        self._session_provider = session_provider
        self._session_provider_read = session_provider_read

    # pylint: disable=R0913
    async def insert_agent(
        self,
        user_id: UUID,
        name: str,
        docker_image: str,
        docker_image_hash: str,
        env_vars: Dict[str, Any],
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
        self,
        agent_id: UUID,
        docker_image: str,
        docker_image_hash: str,
        env_vars: Dict[str, Any],
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

    # pylint: disable=R0913
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
        self,
        agent_id: UUID,
        tee_host_base_url: str,
        agent_instance_id: UUID,
        enclave_cid: str,
        instance_env_vars: Dict[str, Any],
    ) -> UUID:
        data = {
            "id": agent_instance_id,
            "agent_id": agent_id,
            "tee_host_base_url": tee_host_base_url,
            "enclave_cid": enclave_cid,
            "instance_env_vars": json.dumps(instance_env_vars),
            "created_at": utcnow(),
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_INSERT_AGENT_INSTANCE), data)
            await session.commit()
            return agent_instance_id

    async def get_agent_instances(self, is_deleted: Optional[bool] = None) -> List[AgentInstance]:
        results = []
        data = {"is_deleted": is_deleted}
        async with self._session_provider_read.get() as session:
            rows = await session.execute(sqlalchemy.text(SQL_GET_AGENT_INSTANCES), data)
            for row in rows:
                results.append(
                    AgentInstance(
                        id=row.id,
                        agent_id=row.id,
                        tee_host_base_url=row.tee_host_base_url,
                        enclave_cid=row.enclave_cid,
                        instance_env_vars=row.instance_env_vars,
                        pcr0=row.pcr0,
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
                    tee_host_base_url=row.tee_host_base_url,
                    enclave_cid=row.enclave_cid,
                    instance_env_vars=row.instance_env_vars,
                    pcr0=row.pcr0,
                    created_at=row.created_at,
                    last_updated_at=row.last_updated_at,
                )
        return None

    async def delete_agent_instance(self, agent_instance_id: UUID) -> None:
        data = {"id": agent_instance_id}
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_DELETE_AGENT_INSTANCE), data)
            await session.commit()

    async def insert_agent_instance_pcr0(
        self,
        agent_instance_id: UUID,
        pcr0: str,
    ) -> None:
        data = {
            "id": agent_instance_id,
            "pcr0": pcr0,
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_UPDATE_PCR0), data)
            await session.commit()

    async def insert_attestation(
        self,
        agent_instance_id: UUID,
        attestation_details: AttestationDetails,
    ) -> None:
        id = uuid7()
        data = {
            "id": id,
            "agent_instance_id": agent_instance_id,
            "attestation": attestation_details.attestation,
            "valid_from": attestation_details.valid_from,
            "valid_to": attestation_details.valid_to,
            "created_at": utcnow(),
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_INSERT_ATTESTATION), data)
            await session.commit()

    async def get_agent_attestations(self, agent_instance_id: UUID) -> List[Attestation]:
        data = {"agent_instance_id": agent_instance_id}
        results = []
        async with self._session_provider_read.get() as session:
            rows = await session.execute(
                sqlalchemy.text(SQL_GET_ATTESTATIONS_BY_AGENT_INSTANCE_ID), data
            )
            for row in rows:
                results.append(Attestation(
                    id=row.id,
                    agent_instance_id=row.agent_instance_id,
                    attestation=row.attestation,
                    valid_from=row.valid_from,
                    valid_to=row.valid_to,
                    created_at=row.created_at,
                    last_updated_at=row.last_updated_at,
                ))
        return results
