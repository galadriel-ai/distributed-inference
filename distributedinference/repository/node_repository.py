import asyncio
import random
from dataclasses import asdict
from typing import Dict
from typing import List
from typing import Optional
from uuid import UUID

from uuid_extensions import uuid7
from openai.types.chat import ChatCompletionChunk
import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession

from distributedinference import api_logger
from distributedinference.domain.node.entities import ConnectedNode
from distributedinference.domain.node.entities import NodeBenchmark
from distributedinference.domain.node.entities import NodeInfo
from distributedinference.domain.node.entities import NodeMetrics
from distributedinference.domain.node.entities import InferenceError
from distributedinference.domain.node.entities import InferenceRequest
from distributedinference.domain.node.entities import InferenceResponse
from distributedinference.domain.node.entities import NodeStats
from distributedinference.repository import connection
from distributedinference.repository.utils import utcnow

logger = api_logger.get()

SQL_GET_NODE_METRICS = """
SELECT
    id,
    user_profile_id,
    requests_served,
    requests_successful,
    requests_failed,
    time_to_first_token,
    uptime,
    created_at,
    last_updated_at
FROM node_metrics
WHERE user_profile_id = :user_profile_id;
"""

SQL_GET_NODE_METRICS_BY_IDS = """
SELECT
    id,
    user_profile_id,
    requests_served,
    requests_successful,
    requests_failed,
    time_to_first_token,
    uptime,
    created_at,
    last_updated_at
FROM node_metrics
WHERE user_profile_id = ANY(:user_profile_ids);
"""

SQL_INSERT_OR_UPDATE_NODE_METRICS = """
INSERT INTO node_metrics (
    id,
    user_profile_id,
    requests_served,
    requests_successful,
    requests_failed,
    time_to_first_token,
    uptime,
    created_at,
    last_updated_at
) VALUES (
    :id,
    :user_profile_id,
    :requests_served,
    :requests_successful,
    :requests_failed,
    :time_to_first_token,
    :uptime,
    :created_at,
    :last_updated_at
)
ON CONFLICT (user_profile_id) DO UPDATE SET
    requests_served = EXCLUDED.requests_served,
    requests_successful = EXCLUDED.requests_successful,
    requests_failed = EXCLUDED.requests_failed,
    time_to_first_token = EXCLUDED.time_to_first_token,
    uptime = EXCLUDED.uptime,
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
WHERE user_profile_id = :user_profile_id;
"""

SQL_INSERT_OR_UPDATE_NODE_INFO = """
INSERT INTO node_info (
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
) VALUES (
    :id,
    :user_profile_id,
    :gpu_model,
    :vram,
    :cpu_model,
    :cpu_count,
    :ram,
    :network_download_speed,
    :network_upload_speed,
    :operating_system,
    :created_at,
    :last_updated_at
)
ON CONFLICT (user_profile_id) DO UPDATE SET
    gpu_model = EXCLUDED.gpu_model,
    vram = EXCLUDED.vram,
    cpu_model = EXCLUDED.cpu_model,
    cpu_count = EXCLUDED.cpu_count,
    ram = EXCLUDED.ram,
    network_download_speed = EXCLUDED.network_download_speed,
    network_upload_speed = EXCLUDED.network_upload_speed,
    operating_system = EXCLUDED.operating_system,
    last_updated_at = EXCLUDED.last_updated_at;
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
    ni.user_profile_id = :user_profile_id
    AND nb.model_name = :model_name;
"""

SQL_INSERT_OR_UPDATE_NODE_BENCHMARK = """
INSERT INTO node_benchmark (
    id,
    node_id,
    model_name,
    tokens_per_second,
    created_at,
    last_updated_at
) VALUES (
    :id,
    (SELECT id FROM node_info WHERE user_profile_id = :user_profile_id LIMIT 1),
    :model_name,
    :tokens_per_second,
    :created_at,
    :last_updated_at
)
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
FROM node_metrics nm
LEFT JOIN node_info ni on nm.user_profile_id = ni.user_profile_id
LEFT JOIN node_benchmark nb on ni.id = nb.node_id
WHERE nm.user_profile_id = :user_profile_id
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
WHERE ni.user_profile_id = ANY(:user_profile_ids);
"""


class NodeRepository:

    def __init__(self, max_parallel_requests_per_node: int):
        self._max_parallel_requests_per_node = max_parallel_requests_per_node
        # user_id: ConnectedNode
        self._connected_nodes: Dict[UUID, ConnectedNode] = {}

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
            del self._connected_nodes[node_id]

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

    def get_connected_node_info(self, user_id: UUID) -> Optional[ConnectedNode]:
        return self._connected_nodes.get(user_id)

    @connection.read_session
    async def get_node_metrics_by_ids(
        self, node_ids: List[UUID], session: AsyncSession
    ) -> Dict[UUID, NodeMetrics]:
        data = {"user_profile_ids": node_ids}
        rows = await session.execute(sqlalchemy.text(SQL_GET_NODE_METRICS_BY_IDS), data)
        result = {}
        for row in rows:
            result[row.user_profile_id] = NodeMetrics(
                requests_served=row.requests_served,
                requests_successful=row.requests_successful,
                requests_failed=row.requests_failed,
                time_to_first_token=row.time_to_first_token,
                uptime=row.uptime,
            )
        return result

    @connection.read_session
    async def get_node_metrics(
        self, node_id: UUID, session: AsyncSession
    ) -> Optional[NodeMetrics]:
        data = {"user_profile_id": node_id}
        rows = await session.execute(sqlalchemy.text(SQL_GET_NODE_METRICS), data)
        for row in rows:
            return NodeMetrics(
                requests_served=row.requests_served,
                requests_successful=row.requests_successful,
                requests_failed=row.requests_failed,
                time_to_first_token=row.time_to_first_token,
                uptime=row.uptime,
            )
        return None

    async def save_node_metrics(self, node_id: UUID, metrics: NodeMetrics):
        data = {
            "id": str(uuid7()),
            "user_profile_id": node_id,
            "requests_served": metrics.requests_served,
            "requests_successful": metrics.requests_successful,
            "requests_failed": metrics.requests_failed,
            "time_to_first_token": metrics.time_to_first_token,
            "uptime": metrics.uptime,
            "created_at": utcnow(),
            "last_updated_at": utcnow(),
        }
        await connection.write(SQL_INSERT_OR_UPDATE_NODE_METRICS, data)

    @connection.read_session
    async def get_node_info(
        self, user_id: UUID, session: AsyncSession
    ) -> Optional[NodeInfo]:
        data = {"user_profile_id": user_id}
        rows = await session.execute(sqlalchemy.text(SQL_GET_NODE_INFO), data)
        for row in rows:
            return NodeInfo(
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
            "id": str(uuid7()),
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
        await connection.write(SQL_INSERT_OR_UPDATE_NODE_INFO, data)

    @connection.read_session
    async def get_node_benchmark(
        self, user_id: UUID, model_name: str, session: AsyncSession
    ) -> Optional[NodeBenchmark]:
        data = {"user_profile_id": user_id, "model_name": model_name}
        rows = await session.execute(sqlalchemy.text(SQL_GET_NODE_BENCHMARK), data)
        for row in rows:
            return NodeBenchmark(
                model_name=row.model_name,
                tokens_per_second=row.tokens_per_second,
            )
        return None

    @connection.read_session
    async def get_node_stats(
        self, user_id: UUID, session: AsyncSession
    ) -> Optional[NodeStats]:
        data = {"user_profile_id": user_id}
        rows = await session.execute(sqlalchemy.text(SQL_GET_NODE_STATS), data)
        for row in rows:
            return NodeStats(
                requests_served=row.requests_served,
                average_time_to_first_token=row.time_to_first_token,
                benchmark_tokens_per_second=row.benchmark_tokens_per_second,
                benchmark_model_name=row.benchmark_model_name,
                benchmark_created_at=row.benchmark_created_at,
            )
        return None

    @connection.read_session
    async def get_nodes_count(self, session: AsyncSession) -> int:
        data = {}
        rows = await session.execute(sqlalchemy.text(SQL_GET_NODES_COUNT), data)
        for row in rows:
            return row.node_count
        return 0

    @connection.read_session
    async def get_network_throughput(self, session: AsyncSession) -> float:
        connected_user_profile_ids = self.get_connected_node_ids()
        if not connected_user_profile_ids:
            return 0
        data = {"user_profile_ids": tuple([str(i) for i in connected_user_profile_ids])}
        rows = await session.execute(
            sqlalchemy.text(SQL_GET_BENCHMARK_TOKENS_SUM), data
        )
        for row in rows:
            return row.benchmark_sum
        return 0

    async def save_node_benchmark(
        self, user_profile_id: UUID, benchmark: NodeBenchmark
    ):
        data = {
            "id": str(uuid7()),
            "user_profile_id": user_profile_id,
            "model_name": benchmark.model_name,
            "tokens_per_second": benchmark.tokens_per_second,
            "created_at": utcnow(),
            "last_updated_at": utcnow(),
        }
        await connection.write(SQL_INSERT_OR_UPDATE_NODE_BENCHMARK, data)

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
            except Exception as e:
                logger.warning(f"Failed to parse chunk, request_id={request_id}")
        return None

    async def cleanup_request(self, node_id: UUID, request_id: str):
        if node_id in self._connected_nodes:
            connected_node = self._connected_nodes[node_id]
            del connected_node.request_incoming_queues[request_id]
