import asyncio
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict
from typing import Optional
from uuid import UUID

from fastapi import WebSocket
from openai.types.chat import ChatCompletionChunk
from openai.types.chat import CompletionCreateParams


import asyncio
from typing import Optional


class NodeMetrics:
    def __init__(
        self,
        requests_served: int = 0,
        time_to_first_token: Optional[float] = None,
        uptime: int = 0,
    ):
        self._requests_served = requests_served
        self._time_to_first_token = time_to_first_token
        self._uptime = uptime
        self._lock = asyncio.Lock()

    async def get_requests_served(self) -> int:
        async with self._lock:
            return self._requests_served

    async def increment_requests_served(self):
        async with self._lock:
            self._requests_served += 1

    async def get_time_to_first_token(self) -> Optional[float]:
        async with self._lock:
            return self._time_to_first_token

    async def set_time_to_first_token(self, value: float):
        async with self._lock:
            if self._time_to_first_token is None or value < self._time_to_first_token:
                self._time_to_first_token = value

    async def get_uptime(self) -> int:
        async with self._lock:
            return self._uptime

    async def add_uptime(self, value: int):
        async with self._lock:
            self._uptime += value


@dataclass
class NodeInfo:
    gpu_model: Optional[str] = None
    vram: Optional[int] = None
    cpu_model: Optional[str] = None
    cpu_count: Optional[int] = None
    ram: Optional[int] = None
    network_download_speed: Optional[float] = None
    network_upload_speed: Optional[float] = None
    operating_system: Optional[str] = None


@dataclass(frozen=True)
class ConnectedNode:
    uid: UUID
    model: str
    websocket: WebSocket
    request_incoming_queues: Dict[str, asyncio.Queue]
    metrics: NodeMetrics

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
