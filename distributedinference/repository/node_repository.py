import asyncio
import random
from dataclasses import asdict, dataclass
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
from distributedinference.domain.node.entities import NodeStats
from distributedinference.repository import utils
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
    ni.gpu_model,
    ni.vram,
    ni.cpu_model,
    ni.cpu_count,
    ni.ram,
    ni.network_download_speed,
    ni.network_upload_speed,
    ni.operating_system,
    ni.created_at,
    ni.last_updated_at,
    nm.requests_served,
    nm.uptime
FROM node_info ni
LEFT JOIN node_metrics nm on nm.node_info_id = ni.id
WHERE ni.user_profile_id = :user_profile_id
ORDER BY ni.id DESC;
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
    gpu_model,
    vram,
    cpu_model,
    cpu_count,
    ram,
    network_download_speed,
    network_upload_speed,
    operating_system,
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
    cpu_model,
    cpu_count,
    ram,
    network_download_speed,
    network_upload_speed,
    operating_system,
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
    cpu_model = :cpu_model,
    cpu_count = :cpu_count,
    ram = :ram,
    network_download_speed = :network_download_speed,
    network_upload_speed = :network_upload_speed,
    operating_system = :operating_system,
    created_at = :created_at,
    last_updated_at = :last_updated_at
WHERE id = :id;
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

SQL_GET_NODE_STATS = """
SELECT
    nm.requests_served,
    nm.time_to_first_token,
    nb.tokens_per_second AS benchmark_tokens_per_second,
    nb.model_name AS benchmark_model_name,
    nb.created_at AS benchmark_created_at
FROM node_info ni
LEFT JOIN node_metrics nm on nm.node_info_id = ni.id
LEFT JOIN node_benchmark nb on ni.id = nb.node_id
WHERE ni.user_profile_id = :user_profile_id AND ni.id = :id
LIMIT 1;
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
        # user_id: ConnectedNode
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
                        connected=(row.id in self._connected_nodes),
                        created_at=row.created_at,
                    )
                )
            return result

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
            if node.active_requests_count() < self._max_parallel_requests_per_node
        ]

        if not eligible_nodes:
            return None

        min_requests = min(node.active_requests_count() for node in eligible_nodes)
        least_busy_nodes = [
            node
            for node in eligible_nodes
            if node.active_requests_count() == min_requests
        ]

        return random.choice(least_busy_nodes)

    def get_connected_nodes(self) -> List[ConnectedNode]:
        return list(self._connected_nodes.values())

    def get_connected_nodes_count(self) -> int:
        return len(self._connected_nodes)

    def get_connected_node_ids(self) -> List[UUID]:
        return [k for k, _ in self._connected_nodes.items()]

    def get_connected_node_info(self, node_id: UUID) -> Optional[ConnectedNode]:
        return self._connected_nodes.get(node_id)

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
                    gpu_model=row.gpu_model,
                    vram=row.vram,
                    cpu_model=row.cpu_model,
                    cpu_count=row.cpu_count,
                    ram=row.ram,
                    network_download_speed=row.network_download_speed,
                    network_upload_speed=row.network_upload_speed,
                    operating_system=row.operating_system,
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
                    gpu_model=row.gpu_model,
                    vram=row.vram,
                    cpu_model=row.cpu_model,
                    cpu_count=row.cpu_count,
                    ram=row.ram,
                    network_download_speed=row.network_download_speed,
                    network_upload_speed=row.network_upload_speed,
                    operating_system=row.operating_system,
                    created_at=row.created_at,
                )
        return None

    async def save_node_info(self, user_profile_id: UUID, info: NodeInfo):
        data = {
            "id": str(info.node_id),
            "name_alias": info.name_alias,
            "user_profile_id": user_profile_id,
            "gpu_model": info.gpu_model,
            "vram": info.vram,
            "cpu_model": info.cpu_model,
            "cpu_count": info.cpu_count,
            "ram": info.ram,
            "network_download_speed": info.network_download_speed,
            "network_upload_speed": info.network_upload_speed,
            "operating_system": info.operating_system,
            "created_at": utcnow(),
            "last_updated_at": utcnow(),
        }
        async with self._session_provider.get() as session:
            await session.execute(sqlalchemy.text(SQL_UPDATE_NODE_INFO), data)
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

    async def get_node_stats(self, user_id: UUID, node_id: UUID) -> Optional[NodeStats]:
        data = {"id": node_id, "user_profile_id": user_id}
        async with self._session_provider.get() as session:
            result = await session.execute(sqlalchemy.text(SQL_GET_NODE_STATS), data)
            row = result.first()
            if row:
                return NodeStats(
                    requests_served=utils.parse_int(row.requests_served),
                    average_time_to_first_token=utils.parse_float(
                        row.time_to_first_token
                    ),
                    benchmark_tokens_per_second=utils.parse_float(
                        row.benchmark_tokens_per_second
                    ),
                    benchmark_model_name=row.benchmark_model_name,
                    benchmark_created_at=row.benchmark_created_at,
                )
        return None

    async def get_nodes_count(self) -> int:
        async with self._session_provider.get() as session:
            result = await session.execute(sqlalchemy.text(SQL_GET_NODES_COUNT))
            row = result.first()
            if row:
                return row.node_count
        return 0

    async def get_network_throughput(self) -> float:
        connected_node_ids = self.get_connected_node_ids()
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
        connected_node_ids = self.get_connected_node_ids()
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
