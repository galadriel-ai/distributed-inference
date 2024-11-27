import asyncio
import random
import time
from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime
from typing import Dict
from typing import List
from typing import Optional
from uuid import UUID

import sqlalchemy
from fastapi import status as http_status
from openai.types.chat import ChatCompletionChunk
from uuid_extensions import uuid7

from distributedinference import api_logger
from distributedinference.domain.node.entities import ConnectedNode
from distributedinference.domain.node.entities import FullNodeInfo
from distributedinference.domain.node.entities import InferenceError
from distributedinference.domain.node.entities import InferenceErrorStatusCodes
from distributedinference.domain.node.entities import InferenceRequest
from distributedinference.domain.node.entities import InferenceResponse
from distributedinference.domain.node.entities import InferenceStatusCodes
from distributedinference.domain.node.entities import NodeHealth
from distributedinference.domain.node.entities import NodeInfo
from distributedinference.domain.node.entities import NodeMetrics
from distributedinference.domain.node.entities import NodeMetricsIncrement
from distributedinference.domain.node.entities import NodeSpecs
from distributedinference.domain.node.entities import NodeStatus
from distributedinference.domain.node.entities import UserNodeInfo
from distributedinference.repository import utils
from distributedinference.repository.connection import SessionProvider
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
    ni.network_download_speed,
    ni.network_upload_speed,
    ni.operating_system,
    ni.version,
    ni.is_archived,
    ni.created_at,
    ni.last_updated_at,
    nm.requests_served,
    nm.uptime,
    nm.connected_at,
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

SQL_GET_NODE_METRICS_BY_IDS = """
SELECT
    node_metrics.id,
    node_metrics.node_info_id,
    node_metrics.requests_served,
    node_metrics.requests_successful,
    node_metrics.requests_failed,
    node_metrics.time_to_first_token,
    node_metrics.inference_tokens_per_second,
    node_metrics.rtt,
    node_metrics.uptime,
    node_info.gpu_model,
    node_metrics.model_name,
    node_metrics.connected_at,
    node_metrics.created_at,
    node_metrics.last_updated_at,
    node_metrics.status
FROM node_metrics
LEFT JOIN node_info on node_info.id = node_metrics.node_info_id
WHERE node_metrics.node_info_id = ANY(:node_ids);
"""

SQL_GET_ALL_NODE_METRICS = """
SELECT
    node_metrics.id,
    node_metrics.node_info_id,
    node_metrics.requests_served,
    node_metrics.requests_successful,
    node_metrics.requests_failed,
    node_metrics.time_to_first_token,
    node_metrics.inference_tokens_per_second,
    node_metrics.rtt,
    node_metrics.uptime,
    node_info.gpu_model,
    node_metrics.model_name,
    node_metrics.connected_at,
    node_metrics.created_at,
    node_metrics.last_updated_at,
    node_metrics.status
FROM node_metrics
LEFT JOIN node_info on node_info.id = node_metrics.node_info_id
"""

SQL_GET_CONNECTED_NODES_BY_STATUS = """
SELECT
    node_metrics.node_info_id
FROM node_metrics
WHERE node_metrics.node_info_id = ANY(:node_ids) AND node_metrics.status = :status;
"""

SQL_UPDATE_CONNECTED_AT = """
UPDATE node_metrics
SET
    connected_at = :connected_at,
    status = :status,
    last_updated_at = :last_updated_at
WHERE node_info_id = :id;
"""

SQL_UPDATE_NODE_STATUS = """
UPDATE node_metrics
SET
    status = :status,
    last_updated_at = :last_updated_at
WHERE node_info_id = :id;
"""

SQL_CREATE_NODE_METRICS = """
INSERT INTO node_metrics (
    id,
    node_info_id,
    requests_served,
    requests_successful,
    requests_failed,
    time_to_first_token,
    inference_tokens_per_second,
    rtt,
    uptime,
    connected_at,
    model_name,
    status,
    created_at,
    last_updated_at
) VALUES (
    :id,
    :node_id,
    :requests_served_increment,
    :requests_successful_increment,
    :requests_failed_increment,
    :time_to_first_token,
    :inference_tokens_per_second,
    :rtt,
    :uptime_increment,
    :connected_at,
    :model_name,
    :status,
    :created_at,
    :last_updated_at
)
ON CONFLICT (node_info_id) DO UPDATE SET
    requests_served = node_metrics.requests_served + EXCLUDED.requests_served,
    requests_successful = node_metrics.requests_successful + EXCLUDED.requests_successful,
    requests_failed = node_metrics.requests_failed + EXCLUDED.requests_failed,    
    time_to_first_token = COALESCE(EXCLUDED.time_to_first_token, node_metrics.time_to_first_token),
    inference_tokens_per_second = COALESCE(EXCLUDED.inference_tokens_per_second, node_metrics.inference_tokens_per_second),
    rtt = COALESCE(EXCLUDED.rtt, node_metrics.rtt),
    uptime = node_metrics.uptime + EXCLUDED.uptime,
    connected_at = COALESCE(EXCLUDED.connected_at, node_metrics.connected_at),
    model_name = COALESCE(EXCLUDED.model_name, node_metrics.model_name),
    status = COALESCE(EXCLUDED.status, node_metrics.status),
    last_updated_at = EXCLUDED.last_updated_at;
"""

SQL_INCREMENT_NODE_METRICS = """
UPDATE node_metrics SET
    requests_served = requests_served + :requests_served_increment,
    requests_successful = requests_successful + :requests_successful_increment,
    requests_failed = requests_failed + :requests_failed_increment,    
    time_to_first_token = COALESCE(:time_to_first_token, time_to_first_token),
    inference_tokens_per_second = COALESCE(:inference_tokens_per_second, inference_tokens_per_second),
    rtt = COALESCE(:rtt, rtt),
    uptime = uptime + :uptime_increment,
    last_updated_at = :last_updated_at
WHERE node_info_id = :node_info_id;
"""

SQL_GET_NODE_INFO = """
SELECT
    id,
    user_profile_id,
    gpu_model,
    vram,
    gpu_count,
    cpu_model,
    cpu_count,
    ram,
    network_download_speed,
    network_upload_speed,
    operating_system,
    version,
    created_at,
    last_updated_at
FROM node_info
WHERE id = :id AND user_profile_id = :user_profile_id;
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
    network_download_speed,
    network_upload_speed,
    operating_system,
    version,
    created_at,
    last_updated_at
FROM node_info
WHERE name = :node_name AND user_profile_id = :user_profile_id;
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
    network_download_speed = :network_download_speed,
    network_upload_speed = :network_upload_speed,
    operating_system = :operating_system,
    version = :version,
    created_at = :created_at,
    last_updated_at = :last_updated_at
WHERE id = :id;
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

SQL_UPDATE_NODE_CONNECTION_TIMESTAMP = """
UPDATE node_metrics
SET
    connected_at = :connected_at,
    last_updated_at = :last_updated_at
WHERE node_info_id = :id;
"""

SQL_GET_CONNECTED_NODE_COUNT = """
SELECT COUNT(id) AS node_count
FROM node_metrics
WHERE connected_at IS NOT NULL;
"""

SQL_GET_CONNECTED_NODE_IDS = """
SELECT node_info_id
FROM node_metrics
WHERE connected_at IS NOT NULL;
"""

SQL_GET_NODE_METRICS = """
SELECT
    node_info_id AS id,
    requests_served,
    requests_successful,
    requests_failed,
    time_to_first_token,
    inference_tokens_per_second,
    uptime,
    connected_at,
    status
FROM node_metrics
WHERE node_info_id = :id;
"""

SQL_GET_NODES_COUNT = """
SELECT COUNT(id) AS node_count
FROM node_info;
"""

SQL_GET_BENCHMARK_TOKENS_SUM = """
SELECT
    sum(nb.tokens_per_second) AS benchmark_sum
FROM node_benchmark nb
LEFT JOIN node_info ni on nb.node_id = ni.id
WHERE ni.id = ANY(:node_ids);
"""

SQL_GET_BENCHMARK_TOKENS_BY_MODEL = """
SELECT 
    nb.model_name,
    SUM(nb.tokens_per_second) AS benchmark_total_tokens_per_second
FROM node_benchmark nb
LEFT JOIN node_info ni ON nb.node_id = ni.id
WHERE ni.id = ANY(:node_ids)
GROUP BY nb.model_name
ORDER BY benchmark_total_tokens_per_second DESC;
"""

SQL_GET_NODE_STATUS = """
SELECT status
FROM node_metrics
WHERE node_info_id = :node_id
"""

SQL_INSERT_NODE_HEALTH = """
INSERT INTO node_health (
    id,
    node_info_id,
    cpu_percent,
    ram_percent,
    disk_percent,
    gpu_percent,
    vram_percent,
    created_at,
    last_updated_at
)
VALUES (
    :id,
    :node_info_id,
    :cpu_percent,
    :ram_percent,
    :disk_percent,
    :gpu_percent,
    :vram_percent,
    :created_at,
    :last_updated_at
);
"""


@dataclass
class ModelStats:
    model_name: str
    throughput: float


# NodeRepository has too many public methods, over 20
# pylint: disable=R0904
class NodeRepository:

    def __init__(
        self,
        session_provider: SessionProvider,
        session_provider_read: SessionProvider,
        max_parallel_requests_per_node: int,
        max_parallel_requests_per_datacenter_node: int,
    ):
        self._session_provider = session_provider
        self._session_provider_read = session_provider_read
        self._max_parallel_requests_per_node = max_parallel_requests_per_node
        self._max_parallel_requests_per_datacenter_node = (
            max_parallel_requests_per_datacenter_node
        )
        # node_id: ConnectedNode
        self._connected_nodes: Dict[UUID, ConnectedNode] = {}

    @async_timer("node_repository.create_node", logger=logger)
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

    @async_timer("node_repository.get_user_nodes", logger=logger)
    async def get_user_nodes(self, user_profile_id: UUID) -> List[UserNodeInfo]:
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
                        connected=bool(row.connected_at),
                        benchmark_tokens_per_second=row.benchmark_tokens_per_second,
                        is_archived=row.is_archived,
                        created_at=row.created_at,
                    )
                )
            return result

    @async_timer("node_repository.get_user_node_ids", logger=logger)
    async def get_user_node_ids(self, user_profile_id: UUID) -> List[UUID]:
        data = {"user_profile_id": user_profile_id}
        async with self._session_provider_read.get() as session:
            rows = await session.execute(sqlalchemy.text(SQL_GET_USER_NODE_IDS), data)
            results = []
            for row in rows:
                results.append(row.id)
            return results

    @async_timer("node_repository.get_user_node_id_by_name", logger=logger)
    async def get_user_node_id_by_name(
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

    def register_node(self, connected_node: ConnectedNode) -> bool:
        """
        Register a connected node, returns True if the node was successfully registered, False if the node is already registered
        """
        if connected_node.uid not in self._connected_nodes:
            self._connected_nodes[connected_node.uid] = connected_node
            return True
        return False

    def deregister_node(self, node_id: UUID):
        if node_id in self._connected_nodes:
            # Send error to all active requests
            for request_id, queue in self._connected_nodes[
                node_id
            ].request_incoming_queues.items():
                queue.put_nowait(
                    InferenceResponse(
                        node_id=node_id,
                        request_id=request_id,
                        error=InferenceError(
                            status_code=InferenceErrorStatusCodes.UNPROCESSABLE_ENTITY,
                            message="Node disconnected",
                        ),
                    ).to_dict()
                )
            del self._connected_nodes[node_id]

    async def close_node_connection(self, node_id: UUID):
        if node_id in self._connected_nodes:
            await self._connected_nodes[node_id].websocket.close(
                code=http_status.WS_1008_POLICY_VIOLATION,
                reason="No Inference result",
            )

    # pylint: disable=W0613
    def select_node(self, model: str) -> Optional[ConnectedNode]:
        if not self._connected_nodes:
            return None

        eligible_nodes = [
            node
            for node in self._connected_nodes.values()
            if node.model == model and self._can_handle_new_request(node)
        ]

        if not eligible_nodes:
            return None

        return random.choice(eligible_nodes)

    def _can_handle_new_request(self, node: ConnectedNode) -> bool:
        if not node.is_self_hosted and not node.node_status.is_healthy():
            return False
        if node.is_datacenter_gpu():
            return (
                node.active_requests_count()
                < self._max_parallel_requests_per_datacenter_node
            )
        if node.can_handle_parallel_requests():
            return node.active_requests_count() < self._max_parallel_requests_per_node

        return node.active_requests_count() == 1

    @async_timer("node_repository.get_connected_nodes_count", logger=logger)
    async def get_connected_nodes_count(self) -> int:
        async with self._session_provider_read.get() as session:
            result = await session.execute(
                sqlalchemy.text(SQL_GET_CONNECTED_NODE_COUNT)
            )
            return int(result.scalar() or 0)

    @async_timer("node_repository.get_connected_node_ids", logger=logger)
    async def get_connected_node_ids(self) -> List[UUID]:
        async with self._session_provider_read.get() as session:
            result = await session.execute(sqlalchemy.text(SQL_GET_CONNECTED_NODE_IDS))
            return [row.node_info_id for row in result]

    @async_timer("node_repository.get_node_metrics", logger=logger)
    async def get_node_metrics(self, node_id: UUID) -> Optional[NodeMetrics]:
        async with self._session_provider_read.get() as session:
            data = {"id": node_id}
            result = await session.execute(sqlalchemy.text(SQL_GET_NODE_METRICS), data)
            row = result.first()
            if row:
                return NodeMetrics(
                    status=NodeStatus(row.status),
                    requests_served=utils.parse_int(row.requests_served),
                    requests_successful=utils.parse_int(row.requests_successful),
                    requests_failed=utils.parse_int(row.requests_failed),
                    time_to_first_token=row.time_to_first_token,
                    inference_tokens_per_second=row.inference_tokens_per_second,
                    total_uptime=utils.parse_int(row.uptime),
                    current_uptime=(
                        0
                        if not row.connected_at
                        else int(time.time() - row.connected_at.timestamp())
                    ),
                )
        return None

    @async_timer("node_repository.get_node_metrics_by_ids", logger=logger)
    async def get_node_metrics_by_ids(
        self, node_ids: List[UUID]
    ) -> Dict[UUID, NodeMetrics]:
        data = {"node_ids": node_ids}
        async with self._session_provider_read.get() as session:
            rows = await session.execute(
                sqlalchemy.text(SQL_GET_NODE_METRICS_BY_IDS), data
            )
            result = {}
            for row in rows:
                result[row.node_info_id] = NodeMetrics(
                    status=NodeStatus(row.status),
                    requests_served=row.requests_served,
                    requests_successful=row.requests_successful,
                    requests_failed=row.requests_failed,
                    time_to_first_token=row.time_to_first_token,
                    inference_tokens_per_second=row.inference_tokens_per_second,
                    rtt=row.rtt,
                    total_uptime=row.uptime,
                    current_uptime=(
                        0
                        if not row.connected_at
                        else int(time.time() - row.connected_at.timestamp())
                    ),
                    gpu_model=row.gpu_model,
                    model_name=row.model_name,
                    is_active=bool(row.connected_at),
                )
            return result

    @async_timer("node_repository.get_all_node_metrics", logger=logger)
    async def get_all_node_metrics(self) -> Dict[UUID, NodeMetrics]:
        async with self._session_provider_read.get() as session:
            rows = await session.execute(sqlalchemy.text(SQL_GET_ALL_NODE_METRICS))
            result = {}
            for row in rows:
                result[row.node_info_id] = NodeMetrics(
                    status=NodeStatus(row.status),
                    requests_served=row.requests_served,
                    requests_successful=row.requests_successful,
                    requests_failed=row.requests_failed,
                    time_to_first_token=row.time_to_first_token,
                    inference_tokens_per_second=row.inference_tokens_per_second,
                    rtt=row.rtt,
                    total_uptime=row.uptime,
                    current_uptime=(
                        0
                        if not row.connected_at
                        else int(time.time() - row.connected_at.timestamp())
                    ),
                    gpu_model=row.gpu_model,
                    model_name=row.model_name,
                )
            return result

    def get_unhealthy_nodes(self) -> List[ConnectedNode]:
        # returns only in-memory unhealthy nodes
        return [
            node
            for node in self._connected_nodes.values()
            if not node.node_status.is_healthy()
        ]

    def get_locally_connected_nodes(self) -> List[ConnectedNode]:
        return list(self._connected_nodes.values())

    @async_timer("node_repository.get_nodes_for_benchmarking", logger=logger)
    async def get_nodes_for_benchmarking(self) -> List[ConnectedNode]:
        connected_node_ids = list(self._connected_nodes.keys())
        data = {
            "node_ids": connected_node_ids,
            "status": NodeStatus.RUNNING_BENCHMARKING.value,
        }
        node_ids = []
        async with self._session_provider_read.get() as session:
            rows = await session.execute(
                sqlalchemy.text(SQL_GET_CONNECTED_NODES_BY_STATUS), data
            )
            for row in rows:
                node_ids.append(row.node_info_id)
        return [node for node in self._connected_nodes.values() if node.uid in node_ids]

    # Insert if it doesn't exist
    @async_timer("node_repository.set_node_connection_timestamp", logger=logger)
    async def set_node_connection_timestamp(
        self, node_id: UUID, model_name: str, connected_at: datetime, status: NodeStatus
    ):
        data = {
            "id": str(uuid7()),
            "node_id": node_id,
            "requests_served_increment": 0,
            "requests_successful_increment": 0,
            "requests_failed_increment": 0,
            "time_to_first_token": None,
            "inference_tokens_per_second": None,
            "rtt": None,
            "uptime_increment": 0,
            "connected_at": connected_at,
            "model_name": model_name,
            "status": status.value,
            "created_at": utcnow(),
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_CREATE_NODE_METRICS), data)
            await session.commit()

    @async_timer("node_repository.update_node_connection_timestamp", logger=logger)
    async def update_node_to_disconnected(self, node_id: UUID, status: NodeStatus):
        data = {
            "id": node_id,
            "connected_at": None,
            "status": status.value,
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_UPDATE_CONNECTED_AT), data)
            await session.commit()

    @async_timer("node_repository.update_node_status", logger=logger)
    async def update_node_status(self, node_id: UUID, status: NodeStatus):
        data = {
            "id": node_id,
            "status": status.value,
            "last_updated_at": utcnow(),
        }
        if node_id in self._connected_nodes:
            self._connected_nodes[node_id].node_status = status
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_UPDATE_NODE_STATUS), data)
            await session.commit()

    @async_timer("node_repository.increment_node_metrics", logger=logger)
    async def increment_node_metrics(self, metrics: NodeMetricsIncrement):
        data = {
            "node_info_id": metrics.node_id,
            "requests_served_increment": metrics.requests_served_incerement,
            "requests_successful_increment": metrics.requests_successful_incerement,
            "requests_failed_increment": metrics.requests_failed_increment,
            "time_to_first_token": metrics.time_to_first_token,
            "inference_tokens_per_second": metrics.inference_tokens_per_second,
            "rtt": metrics.rtt,
            "uptime_increment": metrics.uptime_increment,
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_INCREMENT_NODE_METRICS), data)
            await session.commit()

    @async_timer("node_repository.get_node_info_by_name", logger=logger)
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

    @async_timer("node_repository.get_node_info_by_name", logger=logger)
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

    @async_timer("node_repository.save_node_info", logger=logger)
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

    @async_timer("node_repository.update_node_name_alias", logger=logger)
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

    @async_timer("node_repository.update_node_archival_status", logger=logger)
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

    @async_timer("node_repository.set_all_connected_nodes_inactive", logger=logger)
    async def set_all_connected_nodes_inactive(self):
        data = {
            "connected_at": None,
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            for node_id in self._connected_nodes:
                data["id"] = node_id
                await session.execute(
                    sqlalchemy.text(SQL_UPDATE_NODE_CONNECTION_TIMESTAMP), data
                )
            await session.commit()

    @async_timer("node_repository.get_nodes_count", logger=logger)
    async def get_nodes_count(self) -> int:
        async with self._session_provider_read.get() as session:
            result = await session.execute(sqlalchemy.text(SQL_GET_NODES_COUNT))
            row = result.first()
            if row:
                return row.node_count
        return 0

    @async_timer("node_repository.get_network_throughput", logger=logger)
    async def get_network_throughput(self) -> float:
        connected_node_ids = await self.get_connected_node_ids()
        if not connected_node_ids:
            return 0
        data = {"node_ids": connected_node_ids}
        async with self._session_provider_read.get() as session:
            result = await session.execute(
                sqlalchemy.text(SQL_GET_BENCHMARK_TOKENS_SUM), data
            )
            row = result.first()
            if row:
                return row.benchmark_sum
        return 0

    @async_timer("node_repository.get_network_model_stats", logger=logger)
    async def get_network_model_stats(self) -> List[ModelStats]:
        connected_node_ids = await self.get_connected_node_ids()
        if not connected_node_ids:
            return []
        data = {"node_ids": connected_node_ids}
        async with self._session_provider_read.get() as session:
            rows = await session.execute(
                sqlalchemy.text(SQL_GET_BENCHMARK_TOKENS_BY_MODEL), data
            )
            return [
                ModelStats(
                    model_name=row.model_name,
                    throughput=row.benchmark_total_tokens_per_second,
                )
                for row in rows
            ]

    @async_timer("node_repository.get_node_status", logger=logger)
    async def get_node_status(self, node_id: UUID) -> Optional[NodeStatus]:
        data = {"node_id": node_id}
        async with self._session_provider_read.get() as session:
            rows = await session.execute(sqlalchemy.text(SQL_GET_NODE_STATUS), data)
            row = rows.first()
            if row:
                return NodeStatus(row.status)
            return None

    @async_timer("node_repository.save_node_health", logger=logger)
    async def save_node_health(self, node_id: UUID, health: NodeHealth):
        data = {
            "id": str(uuid7()),
            "node_info_id": node_id,
            "cpu_percent": health.cpu_percent,
            "ram_percent": health.ram_percent,
            "disk_percent": health.disk_percent,
            "gpu_percent": [gpu.gpu_percent for gpu in health.gpus],
            "vram_percent": [gpu.vram_percent for gpu in health.gpus],
            "created_at": utcnow(),
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_INSERT_NODE_HEALTH), data)
            await session.commit()

    async def send_inference_request(
        self, node_id: UUID, request: InferenceRequest
    ) -> bool:
        if node_id in self._connected_nodes:
            connected_node = self._connected_nodes[node_id]
            connected_node.request_incoming_queues[request.id] = asyncio.Queue()
            await connected_node.websocket.send_json(asdict(request))
            return True
        return False

    async def receive_for_request(
        self, node_id: UUID, request_id: str
    ) -> Optional[InferenceResponse]:
        if node_id in self._connected_nodes:
            connected_node = self._connected_nodes[node_id]
            data = await connected_node.request_incoming_queues[request_id].get()
            try:
                return InferenceResponse(
                    node_id=node_id,
                    request_id=data["request_id"],
                    chunk=(
                        ChatCompletionChunk(**data["chunk"])
                        if data.get("chunk")
                        else None
                    ),
                    error=(
                        InferenceError(**data["error"]) if data.get("error") else None
                    ),
                    status=(
                        InferenceStatusCodes(data["status"])
                        if data.get("status")
                        else None
                    ),
                )
            except Exception:
                logger.warning(f"Failed to parse chunk, request_id={request_id}")
                return None
        return None

    async def cleanup_request(self, node_id: UUID, request_id: str):
        if node_id in self._connected_nodes:
            connected_node = self._connected_nodes[node_id]
            del connected_node.request_incoming_queues[request_id]

    def _get_specs_from_row(self, row):
        specs = None
        if row.cpu_model and row.gpu_model:
            specs = NodeSpecs(
                cpu_model=row.cpu_model,
                cpu_count=row.cpu_count,
                gpu_model=row.gpu_model,
                vram=row.vram,
                ram=row.ram,
                network_download_speed=row.network_download_speed,
                network_upload_speed=row.network_upload_speed,
                operating_system=row.operating_system,
                gpu_count=row.gpu_count,
                version=row.version,
            )
        return specs
