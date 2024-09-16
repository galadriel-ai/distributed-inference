import asyncio

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
    requests_served_incerement: int = 0
    requests_successful_incerement: int = 0
    requests_failed_increment: int = 0
    time_to_first_token: Optional[float] = None
    uptime_increment: int = 0


@dataclass
class NodeMetrics:
    requests_served: int = 0
    requests_successful: int = 0
    requests_failed: int = 0
    time_to_first_token: Optional[float] = None
    uptime: int = 0


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
    created_at: Optional[datetime] = None


@dataclass
class NodeBenchmark:
    node_id: UUID
    model_name: str
    tokens_per_second: float


@dataclass
class NodeStats:
    requests_served: Optional[int] = 0
    average_time_to_first_token: Optional[float] = 0.0

    benchmark_tokens_per_second: Optional[float] = 0
    benchmark_model_name: Optional[str] = None
    benchmark_created_at: Optional[datetime] = None


@dataclass(frozen=True)
class ConnectedNode:
    uid: UUID
    model: str
    connected_at: int
    websocket: WebSocket
    request_incoming_queues: Dict[str, asyncio.Queue]

    def active_requests_count(self) -> int:
        return len(self.request_incoming_queues)


class InferenceStatusCodes(Enum):
    BAD_REQUEST = 400
    AUTHENTICATION_ERROR = 401
    PERMISSION_DENIED = 403
    NOT_FOUND = 404
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    RATE_LIMIT = 429
    UNKNOWN_ERROR = 500


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
    request_id: str
    chunk: Optional[ChatCompletionChunk] = None
    error: Optional[InferenceError] = None

    def to_dict(self):
        return {
            "request_id": self.request_id,
            "error": self.error.to_dict() if self.error else None,
            "chunk": self.chunk.to_dict() if self.chunk else None,
        }
