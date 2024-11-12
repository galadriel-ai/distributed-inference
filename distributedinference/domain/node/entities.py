import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List
from typing import Dict
from typing import Optional
from uuid import UUID

from fastapi import WebSocket
from packaging.version import Version
from openai.types.chat import ChatCompletionChunk
from openai.types.chat import CompletionCreateParams

from distributedinference.service import error_responses


class NodeStatus(Enum):
    RUNNING = "RUNNING"
    RUNNING_BENCHMARKING = "RUNNING_BENCHMARKING"
    RUNNING_DEGRADED = "RUNNING_DEGRADED"
    STOPPED = "STOPPED"
    STOPPED_BENCHMARK_FAILED = "STOPPED_BENCHMARK_FAILED"
    STOPPED_DEGRADED = "STOPPED_DEGRADED"


@dataclass
class NodeMetricsIncrement:
    node_id: UUID
    model: str
    requests_served_incerement: int = 0
    requests_successful_incerement: int = 0
    requests_failed_increment: int = 0
    time_to_first_token: Optional[float] = None
    inference_tokens_per_second: Optional[float] = None
    rtt: Optional[int] = None
    uptime_increment: int = 0


@dataclass
class NodeMetrics:
    requests_served: int = 0
    requests_successful: int = 0
    requests_failed: int = 0
    time_to_first_token: Optional[float] = None
    inference_tokens_per_second: Optional[float] = None
    rtt: Optional[int] = 0
    is_active: bool = False
    total_uptime: int = 0
    current_uptime: int = 0
    gpu_model: str = None
    model_name: str = None


@dataclass
class NodeInfo:
    node_id: UUID
    name: str
    name_alias: str
    cpu_model: Optional[str] = None
    cpu_count: Optional[int] = None
    gpu_model: Optional[str] = None
    gpu_count: Optional[int] = None
    vram: Optional[int] = None
    ram: Optional[int] = None
    network_download_speed: Optional[float] = None
    network_upload_speed: Optional[float] = None
    operating_system: Optional[str] = None
    version: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class UserNodeInfo(NodeInfo):
    connected: bool = False
    requests_served: Optional[int] = None
    uptime: Optional[int] = None
    benchmark_tokens_per_second: Optional[float] = None
    is_archived: bool = False


@dataclass
class NodeBenchmark:
    node_id: UUID
    model_name: str
    benchmark_tokens_per_second: float
    gpu_model: str
    gpu_count: Optional[int] = None


@dataclass
class NodeGPUHealth:
    gpu_percent: int
    vram_percent: int


@dataclass
class NodeHealth:
    node_id: UUID
    cpu_percent: int
    ram_percent: int
    disk_percent: int
    gpus: List[NodeGPUHealth]


@dataclass
class ConnectedNode:
    uid: UUID
    user_id: UUID
    model: str
    vram: int
    connected_at: int  # in seconds
    websocket: WebSocket
    request_incoming_queues: Dict[str, asyncio.Queue]
    node_status: NodeStatus
    is_self_hosted: bool = False
    is_healthy: bool = True
    version: Optional[Version] = None

    def active_requests_count(self) -> int:
        return len(self.request_incoming_queues)

    def is_datacenter_gpu(self) -> bool:
        return self.vram > 80000

    def can_handle_parallel_requests(self) -> bool:
        return self.vram > 8000  # 8GB vram is needed to handle parallel requests

    def is_node_healthy(self) -> bool:
        return self.is_healthy and self.node_status == NodeStatus.RUNNING

    @property
    def current_uptime(self) -> int:
        return int(time.time() - self.connected_at)


class InferenceStatusCodes(Enum):
    RUNNING = 1
    DONE = 2
    ERROR = 3


class InferenceErrorStatusCodes(Enum):
    BAD_REQUEST = 400
    AUTHENTICATION_ERROR = 401
    PERMISSION_DENIED = 403
    NOT_FOUND = 404
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    RATE_LIMIT = 429
    INTERNAL_SERVER_ERROR = 500


@dataclass
class InferenceError:
    status_code: InferenceErrorStatusCodes
    message: str

    def __init__(self, **kwargs):
        try:
            # InferenceErrorStatusCodes(InferenceErrorStatusCodes.BAD_REQUEST) works and int also works
            self.status_code = InferenceErrorStatusCodes(kwargs["status_code"])
            self.message = kwargs["message"]
        except Exception as _:
            self.status_code = InferenceErrorStatusCodes.INTERNAL_SERVER_ERROR
            error = error_responses.InternalServerAPIError()
            self.message = error.to_message()

    def to_dict(self):
        return {
            "status_code": self.status_code.value,
            "message": self.message,
        }


@dataclass
class InferenceRequest:
    id: str
    model: str
    chat_request: CompletionCreateParams


@dataclass
class InferenceResponse:
    node_id: UUID
    request_id: str
    status: Optional[InferenceStatusCodes] = None
    chunk: Optional[ChatCompletionChunk] = None
    error: Optional[InferenceError] = None

    def to_dict(self):
        return {
            "request_id": self.request_id,
            "error": self.error.to_dict() if self.error else None,
            "chunk": self.chunk.to_dict() if self.chunk else None,
            "status": self.status.value if self.status else None,
        }


@dataclass
class CheckHealthResponse:
    node_id: UUID
    is_healthy: bool
    error: Optional[InferenceError] = None
