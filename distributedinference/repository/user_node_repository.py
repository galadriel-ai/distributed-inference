from typing import List
from typing import Optional
from uuid import UUID

import sqlalchemy
from uuid_extensions import uuid7

from distributedinference.api_logger import api_logger
from distributedinference.domain.node.entities import FullNodeInfo
from distributedinference.domain.node.entities import NodeInfo
from distributedinference.domain.node.entities import NodeSpecs
from distributedinference.domain.node.entities import NodeStatus
from distributedinference.domain.node.entities import UserNodeInfo
from distributedinference.repository.connection import DBConnection
from distributedinference.repository.utils import utcnow
from distributedinference.utils.timer import async_timer

logger = api_logger.get()

SQL_CREATE_NODE_INFO = """
INSERT INTO node_info (
    id,
    name,
    name_alias,
    user_profile_id,
    is_archived,
    created_at,
    last_updated_at
) VALUES (
    :id,
    :name,
    :name_alias,
    :user_profile_id,
    :is_archived,
    :created_at,
    :last_updated_at
)
"""

SQL_GET_USER_NODE_INFOS = """
SELECT 
    ni.id,
    ni.name,
    ni.name_alias,
    ni.gpu_model,
    ni.vram,
    ni.gpu_count,
    ni.cpu_model,
    ni.cpu_count,
    ni.ram,
    ni.power_limit,
    ni.network_download_speed,
    ni.network_upload_speed,
    ni.operating_system,
    ni.version,
    ni.is_archived,
    ni.created_at,
    ni.last_updated_at,
    nm.requests_served,
    nm.uptime,
    nm.status,
    nm.rtt,
    nb.tokens_per_second AS benchmark_tokens_per_second
FROM node_info ni
LEFT JOIN node_metrics nm on nm.node_info_id = ni.id
LEFT JOIN node_benchmark nb on nb.node_id = ni.id
WHERE ni.user_profile_id = :user_profile_id
ORDER BY ni.id DESC;
"""

SQL_GET_USER_NODE_IDS = """
SELECT 
    ni.id AS id
FROM node_info ni
WHERE ni.user_profile_id = :user_profile_id;
"""

SQL_GET_USER_NODE_ID_BY_NAME = """
SELECT 
    ni.id AS id
FROM node_info ni
WHERE ni.user_profile_id = :user_profile_id AND name = :name_alias;
"""

SQL_GET_NODE_INFO_BY_NAME = """
SELECT
    id,
    name,
    name_alias,
    user_profile_id,
    gpu_model,
    vram,
    gpu_count,
    cpu_model,
    cpu_count,
    ram,
    power_limit,
    network_download_speed,
    network_upload_speed,
    operating_system,
    version,
    created_at,
    last_updated_at
FROM node_info
WHERE name = :node_name AND user_profile_id = :user_profile_id;
"""

SQL_UPDATE_NODE_NAME_ALIAS = """
UPDATE node_info 
SET 
    name_alias = :name_alias,
    last_updated_at = :last_updated_at
WHERE id = :id;
"""

SQL_UPDATE_NODE_ARCHIVAL_STATUS = """
UPDATE node_info 
SET 
    is_archived = :is_archived,
    last_updated_at = :last_updated_at
WHERE id = :id;
"""

SQL_UPDATE_NODE_INFO = """
UPDATE node_info 
SET 
    name_alias = :name_alias,
    user_profile_id = :user_profile_id,
    gpu_model = :gpu_model,
    vram = :vram,
    gpu_count = :gpu_count,
    cpu_model = :cpu_model,
    cpu_count = :cpu_count,
    ram = :ram,
    power_limit = :power_limit,
    network_download_speed = :network_download_speed,
    network_upload_speed = :network_upload_speed,
    operating_system = :operating_system,
    version = :version,
    created_at = :created_at,
    last_updated_at = :last_updated_at
WHERE id = :id;
"""


class UserNodeRepository:

    def __init__(
        self,
        session_provider: DBConnection,
        session_provider_read: DBConnection,
    ):
        self._session_provider = session_provider
        self._session_provider_read = session_provider_read

    @async_timer("user_node_repository.create_node", logger=logger)
    async def create_node(
        self,
        user_profile_id: UUID,
        name: str,
        name_alias: str,
    ) -> NodeInfo:
        node_id = uuid7()
        created_at = utcnow()
        data = {
            "id": str(node_id),
            "name": name,
            "name_alias": name_alias,
            "user_profile_id": user_profile_id,
            "is_archived": False,
            "status": "CREATED",
            "created_at": created_at,
            "last_updated_at": created_at,
        }
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_CREATE_NODE_INFO), data)
            await session.commit()
            return NodeInfo(
                node_id=node_id,
                name=name,
                name_alias=name_alias,
                created_at=created_at,
                specs=None,
            )

    @async_timer("user_node_repository.get_nodes", logger=logger)
    async def get_nodes(self, user_profile_id: UUID) -> List[UserNodeInfo]:
        data = {"user_profile_id": user_profile_id}
        async with self._session_provider_read.get() as session:
            rows = await session.execute(sqlalchemy.text(SQL_GET_USER_NODE_INFOS), data)
            result = []
            for row in rows:
                specs = self._get_specs_from_row(row)
                result.append(
                    UserNodeInfo(
                        node_id=row.id,
                        name=row.name,
                        name_alias=row.name_alias,
                        specs=specs,
                        requests_served=row.requests_served,
                        uptime=row.uptime,
                        connected=(
                            NodeStatus(row.status).is_connected()
                            if row.status
                            else False
                        ),
                        benchmark_tokens_per_second=row.benchmark_tokens_per_second,
                        is_archived=row.is_archived,
                        created_at=row.created_at,
                    )
                )
            return result

    @async_timer("user_node_repository.get_node_ids", logger=logger)
    async def get_node_ids(self, user_profile_id: UUID) -> List[UUID]:
        data = {"user_profile_id": user_profile_id}
        async with self._session_provider_read.get() as session:
            rows = await session.execute(sqlalchemy.text(SQL_GET_USER_NODE_IDS), data)
            results = []
            for row in rows:
                results.append(row.id)
            return results

    @async_timer("user_node_repository.get_node_id_by_name", logger=logger)
    async def get_node_id_by_name(
        self, user_profile_id: UUID, node_name: str
    ) -> Optional[UUID]:
        data = {"user_profile_id": user_profile_id, "name_alias": node_name}
        async with self._session_provider_read.get() as session:
            result = await session.execute(
                sqlalchemy.text(SQL_GET_USER_NODE_ID_BY_NAME), data
            )
            row = result.first()
            if row:
                return row.id
            return None

    @async_timer("user_node_repository.get_node_info_by_name", logger=logger)
    async def get_node_info_by_name(
        self, user_id: UUID, node_name: str
    ) -> Optional[NodeInfo]:
        data = {"node_name": node_name, "user_profile_id": user_id}
        async with self._session_provider_read.get() as session:
            result = await session.execute(
                sqlalchemy.text(SQL_GET_NODE_INFO_BY_NAME), data
            )
            row = result.first()
            if row:
                specs = self._get_specs_from_row(row)
                return NodeInfo(
                    node_id=row.id,
                    name=row.name,
                    name_alias=row.name_alias,
                    created_at=row.created_at,
                    specs=specs,
                )
        return None

    @async_timer("user_node_repository.get_node_info_by_name", logger=logger)
    async def get_full_node_info_by_name(
        self, user_id: UUID, node_name: str
    ) -> Optional[FullNodeInfo]:
        data = {"node_name": node_name, "user_profile_id": user_id}
        async with self._session_provider_read.get() as session:
            result = await session.execute(
                sqlalchemy.text(SQL_GET_NODE_INFO_BY_NAME), data
            )
            row = result.first()
            if row and row.gpu_model and row.cpu_model:
                specs = self._get_specs_from_row(row)
                if not specs:
                    return None
                return FullNodeInfo(
                    node_id=row.id,
                    name=row.name,
                    name_alias=row.name_alias,
                    created_at=row.created_at,
                    specs=specs,
                )
        return None

    @async_timer("user_node_repository.update_node_name_alias", logger=logger)
    async def update_node_name_alias(
        self,
        node_id: UUID,
        updated_name_alias: str,
    ):
        data = {
            "id": node_id,
            "name_alias": updated_name_alias,
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_UPDATE_NODE_NAME_ALIAS), data)
            await session.commit()

    @async_timer("user_node_repository.update_node_archival_status", logger=logger)
    async def update_node_archival_status(
        self,
        node_id: UUID,
        is_archived: bool,
    ):
        data = {
            "id": node_id,
            "is_archived": is_archived,
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            await session.execute(
                sqlalchemy.text(SQL_UPDATE_NODE_ARCHIVAL_STATUS), data
            )
            await session.commit()

    @async_timer("user_node_repository.save_node_info", logger=logger)
    async def save_node_info(self, user_profile_id: UUID, node_info: FullNodeInfo):
        data = {
            "id": str(node_info.node_id),
            "name_alias": node_info.name_alias,
            "user_profile_id": user_profile_id,
            "gpu_model": node_info.specs.gpu_model,
            "vram": node_info.specs.vram,
            "gpu_count": node_info.specs.gpu_count,
            "cpu_model": node_info.specs.cpu_model,
            "cpu_count": node_info.specs.cpu_count,
            "ram": node_info.specs.ram,
            "power_limit": node_info.specs.power_limit,
            "network_download_speed": node_info.specs.network_download_speed,
            "network_upload_speed": node_info.specs.network_upload_speed,
            "operating_system": node_info.specs.operating_system,
            "version": node_info.specs.version,
            "created_at": utcnow(),
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_UPDATE_NODE_INFO), data)
            await session.commit()

    def _get_specs_from_row(self, row):
        specs = None
        if row.cpu_model and row.gpu_model:
            specs = NodeSpecs(
                cpu_model=row.cpu_model,
                cpu_count=row.cpu_count,
                gpu_model=row.gpu_model,
                vram=row.vram,
                ram=row.ram,
                power_limit=row.power_limit,
                network_download_speed=row.network_download_speed,
                network_upload_speed=row.network_upload_speed,
                operating_system=row.operating_system,
                gpu_count=row.gpu_count,
                version=row.version,
            )
        return specs
