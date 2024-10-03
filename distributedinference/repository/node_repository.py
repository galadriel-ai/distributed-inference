import asyncio
import random
from dataclasses import asdict
from dataclasses import dataclass
from typing import Dict
from typing import List
from typing import Optional
from uuid import UUID

from uuid_extensions import uuid7
from openai.types.chat import ChatCompletionChunk
import sqlalchemy

from distributedinference import api_logger
from distributedinference.domain.node.entities import ConnectedNode
from distributedinference.domain.node.entities import NodeBenchmark
from distributedinference.domain.node.entities import NodeInfo
from distributedinference.domain.node.entities import NodeMetrics
from distributedinference.domain.node.entities import UserNodeInfo
from distributedinference.domain.node.entities import InferenceError
from distributedinference.domain.node.entities import InferenceRequest
from distributedinference.domain.node.entities import InferenceResponse
from distributedinference.domain.node.entities import InferenceStatusCodes
from distributedinference.domain.node.entities import NodeMetricsIncrement
from distributedinference.repository.connection import SessionProvider
from distributedinference.repository.utils import utcnow

logger = api_logger.get()

SQL_CREATE_NODE_INFO = """
INSERT INTO node_info (
    id,
    name,
    name_alias,
    user_profile_id,
    created_at,
    last_updated_at
) VALUES (
    :id,
    :name,
    :name_alias,
    :user_profile_id,
    :created_at,
    :last_updated_at
)
"""

SQL_GET_USER_NODE_INFOS = """
SELECT 
    ni.id,
    ni.name,
    ni.name_alias,
    ni.is_active,
    ni.gpu_model,
    ni.vram,
    ni.cpu_model,
    ni.cpu_count,
    ni.ram,
    ni.network_download_speed,
    ni.network_upload_speed,
    ni.operating_system,
    ni.version,
    ni.created_at,
    ni.last_updated_at,
    nm.requests_served,
    nm.uptime,
    nb.tokens_per_second
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
    id,
    node_info_id,
    requests_served,
    requests_successful,
    requests_failed,
    time_to_first_token,
    uptime,
    created_at,
    last_updated_at
FROM node_metrics
WHERE node_info_id = ANY(:node_ids);
"""

SQL_INCREMENT_NODE_METRICS = """
INSERT INTO node_metrics (
    id,
    node_info_id,
    requests_served,
    requests_successful,
    requests_failed,
    time_to_first_token,
    uptime,
    created_at,
    last_updated_at
) VALUES (
    :id,
    :node_id,
    :requests_served_increment,
    :requests_successful_increment,
    :requests_failed_increment,
    :time_to_first_token,
    :uptime_increment,
    :created_at,
    :last_updated_at
)
ON CONFLICT (node_info_id) DO UPDATE SET
    requests_served = node_metrics.requests_served + EXCLUDED.requests_served,
    requests_successful = node_metrics.requests_successful + EXCLUDED.requests_successful,
    requests_failed = node_metrics.requests_failed + EXCLUDED.requests_failed,
    time_to_first_token = COALESCE(EXCLUDED.time_to_first_token, node_metrics.time_to_first_token),
    uptime = node_metrics.uptime + EXCLUDED.uptime,
    last_updated_at = EXCLUDED.last_updated_at;
"""

SQL_GET_NODE_INFO = """
SELECT
    id,
    user_profile_id,
    is_active,
    gpu_model,
    vram,
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
    is_active,
    gpu_model,
    vram,
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
    is_active = :is_active,
    gpu_model = :gpu_model,
    vram = :vram,
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

SQL_UPDATE_NODE_ACTIVE_FLAG = """
UPDATE node_info
SET
    is_active = :is_active,
    last_updated_at = :last_updated_at
WHERE id = :id;
"""

SQL_GET_CONNECTED_NODES = """
SELECT
    ni.id,
    ni.name,
    nb.model_name,
    nb.tokens_per_second
FROM node_info ni
LEFT JOIN node_benchmark nb on ni.id = nb.node_id
WHERE ni.is_active = True;
"""

SQL_GET_CONNECTED_NODE_COUNT = """
SELECT COUNT(id) AS node_count
FROM node_info
WHERE is_active = True;
"""

# Get all the node id of connected nodes
SQL_GET_CONNECTED_NODE_IDS = """
SELECT id
FROM node_info
WHERE is_active = True;
"""

SQL_GET_CONNECTED_NODE_METRIC = """
SELECT
    ni.id,
    nm.requests_served,
    nm.requests_successful,
    nm.requests_failed,
    nm.time_to_first_token,
    nm.uptime
FROM node_info ni
LEFT JOIN node_metrics nm on nm.node_info_id = ni.id
WHERE ni.is_active = True AND ni.id = :id;
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
    SUM(nb.tokens_per_second) AS total_tokens_per_second
FROM node_benchmark nb
LEFT JOIN node_info ni ON nb.node_id = ni.id
WHERE ni.id = ANY(:node_ids)
GROUP BY nb.model_name
ORDER BY total_tokens_per_second DESC;
"""


@dataclass
class ModelStats:
    model_name: str
    throughput: float


# NodeRepository has too many public methods, over 20
# pylint: disable=R0904
class NodeRepository:

    def __init__(
        self, session_provider: SessionProvider, max_parallel_requests_per_node: int
    ):
        self._session_provider = session_provider
        self._max_parallel_requests_per_node = max_parallel_requests_per_node
        # node_id: ConnectedNode
        self._connected_nodes: Dict[UUID, ConnectedNode] = {}

    async def create_node(
        self,
        user_profile_id: UUID,
        name: str,
        name_alias: str,
    ) -> NodeInfo:
        node_id = uuid7()
        data = {
            "id": str(node_id),
            "name": name,
            "name_alias": name_alias,
            "user_profile_id": user_profile_id,
            "created_at": utcnow(),
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_CREATE_NODE_INFO), data)
            await session.commit()
            return NodeInfo(node_id=node_id, name=name, name_alias=name_alias)

    async def get_user_nodes(self, user_profile_id: UUID) -> List[UserNodeInfo]:
        data = {"user_profile_id": user_profile_id}
        async with self._session_provider.get() as session:
            rows = await session.execute(sqlalchemy.text(SQL_GET_USER_NODE_INFOS), data)
            result = []
            for row in rows:
                result.append(
                    UserNodeInfo(
                        node_id=row.id,
                        name=row.name,
                        name_alias=row.name_alias,
                        gpu_model=row.gpu_model,
                        vram=row.vram,
                        cpu_model=row.cpu_model,
                        cpu_count=row.cpu_count,
                        ram=row.ram,
                        network_download_speed=row.network_download_speed,
                        network_upload_speed=row.network_upload_speed,
                        operating_system=row.operating_system,
                        requests_served=row.requests_served,
                        uptime=row.uptime,
                        connected=row.is_active,
                        tokens_per_second=row.tokens_per_second,
                        created_at=row.created_at,
                    )
                )
            return result

    async def get_user_node_ids(self, user_profile_id: UUID) -> List[UUID]:
        data = {"user_profile_id": user_profile_id}
        async with self._session_provider.get() as session:
            rows = await session.execute(sqlalchemy.text(SQL_GET_USER_NODE_IDS), data)
            results = []
            for row in rows:
                results.append(row.id)
            return results

    async def get_user_node_id_by_name(
        self, user_profile_id: UUID, node_name: str
    ) -> Optional[UUID]:
        data = {"user_profile_id": user_profile_id, "name_alias": node_name}
        async with self._session_provider.get() as session:
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
                            status_code=InferenceStatusCodes.UNPROCESSABLE_ENTITY,
                            message="Node disconnected",
                        ),
                    ).to_dict()
                )
            del self._connected_nodes[node_id]

    # pylint: disable=W0613
    def select_node(self, model: str) -> Optional[ConnectedNode]:
        if not self._connected_nodes:
            return None

        eligible_nodes = [
            node
            for node in self._connected_nodes.values()
            if self._can_handle_new_request(node)
        ]

        if not eligible_nodes:
            return None

        max_capacity_left = max(self._capacity_left(node) for node in eligible_nodes)
        # Select all nodes with the maximum capacity
        nodes_with_max_capacity_left = [
            node
            for node in eligible_nodes
            if self._capacity_left(node) == max_capacity_left
        ]

        # Randomly choose one node from those with maximum capacity
        return random.choice(nodes_with_max_capacity_left)

    def _can_handle_new_request(self, node: ConnectedNode) -> bool:
        if node.can_handle_parallel_requests():
            return node.active_requests_count() < self._max_parallel_requests_per_node

        return node.active_requests_count() == 1

    def _capacity_left(self, node: ConnectedNode) -> int:
        if node.can_handle_parallel_requests():
            return self._max_parallel_requests_per_node - node.active_requests_count()

        return 1 - node.active_requests_count()

    async def get_connected_node_benchmarks(self) -> List[NodeBenchmark]:
        async with self._session_provider.get() as session:
            rows = await session.execute(sqlalchemy.text(SQL_GET_CONNECTED_NODES))
            return [
                NodeBenchmark(
                    node_id=row.id,
                    model_name=row.model_name,
                    tokens_per_second=row.tokens_per_second,
                )
                for row in rows
            ]

    async def get_connected_nodes_count(self) -> int:
        async with self._session_provider.get() as session:
            result = await session.execute(
                sqlalchemy.text(SQL_GET_CONNECTED_NODE_COUNT)
            )
            return int(result.scalar())

    async def get_connected_node_ids(self) -> List[UUID]:
        async with self._session_provider.get() as session:
            result = await session.execute(sqlalchemy.text(SQL_GET_CONNECTED_NODE_IDS))
            return [row.id for row in result]

    async def get_connected_node_metrics(self, node_id: UUID) -> Optional[NodeMetrics]:
        async with self._session_provider.get() as session:
            data = {"id": node_id}
            result = await session.execute(
                sqlalchemy.text(SQL_GET_CONNECTED_NODE_METRIC), data
            )
            row = result.first()
            if row:
                return NodeMetrics(
                    requests_served=row.requests_served,
                    requests_successful=row.requests_successful,
                    requests_failed=row.requests_failed,
                    time_to_first_token=row.time_to_first_token,
                    uptime=row.uptime,
                )

    async def get_node_metrics_by_ids(
        self, node_ids: List[UUID]
    ) -> Dict[UUID, NodeMetrics]:
        data = {"node_ids": node_ids}
        async with self._session_provider.get() as session:
            rows = await session.execute(
                sqlalchemy.text(SQL_GET_NODE_METRICS_BY_IDS), data
            )
            result = {}
            for row in rows:
                result[row.node_info_id] = NodeMetrics(
                    requests_served=row.requests_served,
                    requests_successful=row.requests_successful,
                    requests_failed=row.requests_failed,
                    time_to_first_token=row.time_to_first_token,
                    uptime=row.uptime,
                )
            return result

    async def increment_node_metrics(self, metrics: NodeMetricsIncrement):
        data = {
            "id": str(uuid7()),
            "node_id": metrics.node_id,
            "requests_served_increment": metrics.requests_served_incerement,
            "requests_successful_increment": metrics.requests_successful_incerement,
            "requests_failed_increment": metrics.requests_failed_increment,
            "time_to_first_token": metrics.time_to_first_token,
            "uptime_increment": metrics.uptime_increment,
            "created_at": utcnow(),
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_INCREMENT_NODE_METRICS), data)
            await session.commit()

    async def get_node_info(self, user_id: UUID, node_id: UUID) -> Optional[NodeInfo]:
        data = {"id": node_id, "user_profile_id": user_id}
        async with self._session_provider.get() as session:
            result = await session.execute(sqlalchemy.text(SQL_GET_NODE_INFO), data)
            row = result.first()
            if row:
                return NodeInfo(
                    node_id=row.id,
                    name=row.name,
                    name_alias=row.name_alias,
                    is_active=row.is_active,
                    gpu_model=row.gpu_model,
                    vram=row.vram,
                    cpu_model=row.cpu_model,
                    cpu_count=row.cpu_count,
                    ram=row.ram,
                    network_download_speed=row.network_download_speed,
                    network_upload_speed=row.network_upload_speed,
                    operating_system=row.operating_system,
                    version=row.version,
                    created_at=row.created_at,
                )
        return None

    async def get_node_info_by_name(
        self, user_id: UUID, node_name: str
    ) -> Optional[NodeInfo]:
        data = {"node_name": node_name, "user_profile_id": user_id}
        async with self._session_provider.get() as session:
            result = await session.execute(
                sqlalchemy.text(SQL_GET_NODE_INFO_BY_NAME), data
            )
            row = result.first()
            if row:
                return NodeInfo(
                    node_id=row.id,
                    name=row.name,
                    name_alias=row.name_alias,
                    is_active=row.is_active,
                    gpu_model=row.gpu_model,
                    vram=row.vram,
                    cpu_model=row.cpu_model,
                    cpu_count=row.cpu_count,
                    ram=row.ram,
                    network_download_speed=row.network_download_speed,
                    network_upload_speed=row.network_upload_speed,
                    operating_system=row.operating_system,
                    version=row.version,
                    created_at=row.created_at,
                )
        return None

    async def save_node_info(self, user_profile_id: UUID, info: NodeInfo):
        data = {
            "id": str(info.node_id),
            "name_alias": info.name_alias,
            "is_active": info.is_active,
            "user_profile_id": user_profile_id,
            "gpu_model": info.gpu_model,
            "vram": info.vram,
            "cpu_model": info.cpu_model,
            "cpu_count": info.cpu_count,
            "ram": info.ram,
            "network_download_speed": info.network_download_speed,
            "network_upload_speed": info.network_upload_speed,
            "operating_system": info.operating_system,
            "version": info.version,
            "created_at": utcnow(),
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_UPDATE_NODE_INFO), data)
            await session.commit()

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

    async def set_node_active_status(self, node_id: UUID, is_active: bool):
        data = {
            "id": node_id,
            "is_active": is_active,
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_UPDATE_NODE_ACTIVE_FLAG), data)
            await session.commit()

    async def set_all_connected_nodes_inactive(self):
        data = {
            "is_active": False,
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            for node_id in self._connected_nodes:
                data["id"] = node_id
                await session.execute(
                    sqlalchemy.text(SQL_UPDATE_NODE_ACTIVE_FLAG), data
                )
            await session.commit()

    async def get_nodes_count(self) -> int:
        async with self._session_provider.get() as session:
            result = await session.execute(sqlalchemy.text(SQL_GET_NODES_COUNT))
            row = result.first()
            if row:
                return row.node_count
        return 0

    async def get_network_throughput(self) -> float:
        connected_node_ids = await self.get_connected_node_ids()
        if not connected_node_ids:
            return 0
        data = {"node_ids": tuple(str(i) for i in connected_node_ids)}
        async with self._session_provider.get() as session:
            result = await session.execute(
                sqlalchemy.text(SQL_GET_BENCHMARK_TOKENS_SUM), data
            )
            row = result.first()
            if row:
                return row.benchmark_sum
        return 0

    async def get_network_model_stats(self) -> List[ModelStats]:
        connected_node_ids = await self.get_connected_node_ids()
        if not connected_node_ids:
            return []
        data = {"node_ids": tuple(str(i) for i in connected_node_ids)}
        async with self._session_provider.get() as session:
            rows = await session.execute(
                sqlalchemy.text(SQL_GET_BENCHMARK_TOKENS_BY_MODEL), data
            )
            return [
                ModelStats(
                    model_name=row.model_name, throughput=row.total_tokens_per_second
                )
                for row in rows
            ]

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
                )
            except Exception:
                logger.warning(f"Failed to parse chunk, request_id={request_id}")
        return None

    async def cleanup_request(self, node_id: UUID, request_id: str):
        if node_id in self._connected_nodes:
            connected_node = self._connected_nodes[node_id]
            del connected_node.request_incoming_queues[request_id]
