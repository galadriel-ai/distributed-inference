import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Tuple
from typing import List
from typing import Optional
from uuid import UUID

import sqlalchemy
from uuid_extensions import uuid7

from distributedinference import api_logger
from distributedinference.domain.node.entities import ConnectedNode, BackendHost
from distributedinference.domain.node.entities import NodeHealth
from distributedinference.domain.node.entities import NodeMetrics
from distributedinference.domain.node.entities import NodeMetricsIncrement
from distributedinference.domain.node.entities import NodeStatus
from distributedinference.repository import utils
from distributedinference.repository.connection import SessionProvider
from distributedinference.repository.utils import utcnow
from distributedinference.utils.timer import async_timer

logger = api_logger.get()

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
    connected_host = :connected_host,
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
    connected_host,
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
    :connected_host,
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
    connected_host = COALESCE(EXCLUDED.connected_host, node_metrics.connected_host),
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

SQL_UPDATE_NODE_CONNECTION_TIMESTAMP_AND_STATUS = """
UPDATE node_metrics
SET
    status = :status,
    connected_at = :connected_at,
    connected_host = :connected_host,
    last_updated_at = :last_updated_at
WHERE node_info_id = :id;
"""

SQL_GET_CONNECTED_NODE_COUNT = """
SELECT COUNT(id) AS node_count
FROM node_metrics
WHERE status::text LIKE 'RUNNING%';
"""

SQL_GET_CONNECTED_NODE_IDS = """
SELECT node_info_id
FROM node_metrics
WHERE status::text LIKE 'RUNNING%';
"""

SQL_GET_CONNECTED_NODES_TO_THE_CURRENT_BACKEND = """
SELECT node_info_id
FROM node_metrics
WHERE status::text LIKE 'RUNNING%' AND connected_host::text = :connected_host;
"""

SQL_GET_RUNNING_NODES_WITHOUT_CONNECTED_HOST = """
SELECT node_info_id, status
FROM node_metrics
WHERE status::text LIKE 'RUNNING%' AND connected_host IS NULL;
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
    connected_host,
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
    power_percent,
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
    :power_percent,
    :created_at,
    :last_updated_at
);
"""


@dataclass
class ModelStats:
    model_name: str
    throughput: float


class NodeRepository:

    def __init__(
        self,
        session_provider: SessionProvider,
        session_provider_read: SessionProvider,
    ):
        self._session_provider = session_provider
        self._session_provider_read = session_provider_read

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
                    is_active=(
                        NodeStatus(row.status).is_active() if row.status else False
                    ),
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

    @async_timer("node_repository.get_nodes_for_benchmarking", logger=logger)
    async def get_nodes_for_benchmarking(
        self, connected_nodes: List[ConnectedNode]
    ) -> List[ConnectedNode]:
        connected_node_ids = [node.uid for node in connected_nodes]
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
        return [node for node in connected_nodes if node.uid in node_ids]

    # Insert if it doesn't exist
    # pylint: disable=too-many-arguments
    @async_timer("node_repository.set_node_connection_timestamp", logger=logger)
    async def set_node_connection_timestamp(
        self,
        node_id: UUID,
        model_name: str,
        connected_at: datetime,
        connected_host: BackendHost,
        status: NodeStatus,
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
            "connected_host": connected_host,
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
            "connected_host": None,
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

    @async_timer("node_repository.set_nodes_inactive", logger=logger)
    async def set_nodes_inactive(self, nodes: List[ConnectedNode]):
        async with self._session_provider.get() as session:
            for node in nodes:
                data = {
                    "id": node.uid,
                    "status": node.node_status.value,
                    "connected_at": None,
                    "connected_host": None,
                    "last_updated_at": utcnow(),
                }
                await session.execute(
                    sqlalchemy.text(SQL_UPDATE_NODE_CONNECTION_TIMESTAMP_AND_STATUS),
                    data,
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
            "power_percent": _get_healthcheck_power_percent(health),
            "created_at": utcnow(),
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_INSERT_NODE_HEALTH), data)
            await session.commit()

    @async_timer(
        "node_repository.get_connected_nodes_to_the_current_backend", logger=logger
    )
    async def get_connected_nodes_to_the_current_backend(
        self, backend_host: BackendHost
    ) -> List[UUID]:
        async with self._session_provider_read.get() as session:
            data = {"connected_host": backend_host.value}
            result = await session.execute(
                sqlalchemy.text(SQL_GET_CONNECTED_NODES_TO_THE_CURRENT_BACKEND), data
            )
            return [row.node_info_id for row in result]

    @async_timer(
        "node_repository.get_running_nodes_without_connected_host", logger=logger
    )
    async def get_running_nodes_without_connected_host(
        self,
    ) -> List[Tuple[UUID, NodeStatus]]:
        async with self._session_provider_read.get() as session:
            result = await session.execute(
                sqlalchemy.text(SQL_GET_RUNNING_NODES_WITHOUT_CONNECTED_HOST)
            )
            return [(row.node_info_id, NodeStatus(row.status)) for row in result]


def _get_healthcheck_power_percent(health: NodeHealth):
    if not health.gpus or health.gpus[0].power_percent is None:
        return []
    return [gpu.power_percent for gpu in health.gpus]
