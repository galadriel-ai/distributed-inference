import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict
from typing import Optional
from uuid import UUID

from fastapi import WebSocket
from openai.types.chat import ChatCompletionChunk
from openai.types.chat import CompletionCreateParams


@dataclass
class NodeMetricsIncrement:
    node_id: UUID
    model: str
    requests_served_incerement: int = 0
    requests_successful_incerement: int = 0
    requests_failed_increment: int = 0
    time_to_first_token: Optional[float] = None
    inference_tokens_per_second: Optional[float] = None
    rtt: int = 0
    uptime_increment: int = 0


@dataclass
class NodeMetrics:
    requests_served: int = 0
    requests_successful: int = 0
    requests_failed: int = 0
    time_to_first_token: Optional[float] = None
    inference_tokens_per_second: Optional[float] = None
    rtt: int = 0
    is_active: bool = False
    total_uptime: int = 0
    current_uptime: int = 0
    gpu_model: str = None


@dataclass
class NodeInfo:
    node_id: UUID
    name: str
    name_alias: str
    cpu_model: Optional[str] = None
    cpu_count: Optional[int] = None
    gpu_model: Optional[str] = None
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


@dataclass
class NodeBenchmark:
    node_id: UUID
    model_name: str
    benchmark_tokens_per_second: float
    gpu_model: str


@dataclass()
class ConnectedNode:
    uid: UUID
    user_id: UUID
    model: str
    vram: int
    connected_at: int  # in seconds
    websocket: WebSocket
    request_incoming_queues: Dict[str, asyncio.Queue]
    is_healthy: bool = True

    def active_requests_count(self) -> int:
        return len(self.request_incoming_queues)

    def is_datacenter_gpu(self) -> bool:
        return self.vram > 80000

    def can_handle_parallel_requests(self) -> bool:
        return self.vram > 8000  # 8GB vram is needed to handle parallel requests

    @property
    def current_uptime(self) -> int:
        return int(time.time() - self.connected_at)


class InferenceStatusCodes(Enum):
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
    status_code: InferenceStatusCodes
    message: str

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
    chunk: Optional[ChatCompletionChunk] = None
    error: Optional[InferenceError] = None

    def to_dict(self):
        return {
            "request_id": self.request_id,
            "error": self.error.to_dict() if self.error else None,
            "chunk": self.chunk.to_dict() if self.chunk else None,
        }


@dataclass
class CheckHealthResponse:
    node_id: UUID
    is_healthy: bool
    error: Optional[InferenceError] = None
