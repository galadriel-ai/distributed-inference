import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict
from typing import List
from typing import Optional
from uuid import UUID

from fastapi import WebSocket
from openai.types.chat import ChatCompletionChunk
from openai.types.chat import CompletionCreateParams
from packaging.version import Version
from pydantic import BaseModel, Field

from distributedinference.service import error_responses


class NodeStatus(Enum):
    RUNNING = "RUNNING"
    RUNNING_BENCHMARKING = "RUNNING_BENCHMARKING"
    RUNNING_DEGRADED = "RUNNING_DEGRADED"
    # node can only get into the *_DISABLED status manually
    # to get out of the DISABLED status also needs manual intervention
    RUNNING_DISABLED = "RUNNING_DISABLED"
    STOPPED = "STOPPED"
    STOPPED_BENCHMARK_FAILED = "STOPPED_BENCHMARK_FAILED"
    STOPPED_DEGRADED = "STOPPED_DEGRADED"
    STOPPED_DISABLED = "STOPPED_DISABLED"

    def is_connected(self):
        return self in [
            NodeStatus.RUNNING,
            NodeStatus.RUNNING_BENCHMARKING,
            NodeStatus.RUNNING_DEGRADED,
            NodeStatus.RUNNING_DISABLED,
        ]

    def is_active(self):
        return self in [
            NodeStatus.RUNNING,
            NodeStatus.RUNNING_DEGRADED,
            NodeStatus.RUNNING_DISABLED,
        ]

    def is_healthy(self):
        return self in [NodeStatus.RUNNING]

    def is_disabled(self):
        return self in [NodeStatus.RUNNING_DISABLED, NodeStatus.STOPPED_DISABLED]

    def description(self):
        description = "Unknown"
        match self:
            case NodeStatus.RUNNING:
                description = "Running"
            case NodeStatus.RUNNING_BENCHMARKING:
                description = "Running - verifying performance"
            case NodeStatus.RUNNING_DEGRADED:
                description = "Running - performance degraded"
            case NodeStatus.RUNNING_DISABLED:
                description = "Running"
            case NodeStatus.STOPPED:
                description = "Stopped"
            case NodeStatus.STOPPED_BENCHMARK_FAILED:
                description = "Stopped"
            case NodeStatus.STOPPED_DEGRADED:
                description = "Stopped"
            case NodeStatus.STOPPED_DISABLED:
                description = "Stopped"
        return description

class BackendHost(Enum):
    DISTRIBUTED_INFERENCE_EU = "DISTRIBUTED_INFERENCE_EU"
    DISTRIBUTED_INFERENCE_US = "DISTRIBUTED_INFERENCE_US"


    @staticmethod
    def normalize(value: str) -> str:
        return value.upper().replace("-", "_")

    # from function to handle snake case and lowercase values e.g. distributed-inference-eu
    @classmethod
    def from_value(cls, value: str) -> "BackendHost":
        normalized_value = cls.normalize(value)
        return cls(normalized_value)


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
    status: NodeStatus
    requests_served: int = 0
    requests_successful: int = 0
    requests_failed: int = 0
    time_to_first_token: Optional[float] = None
    inference_tokens_per_second: Optional[float] = None
    rtt: Optional[int] = 0
    is_active: bool = False
    total_uptime: int = 0
    current_uptime: int = 0
    gpu_model: Optional[str] = None
    model_name: Optional[str] = None


@dataclass
class NodeSpecs:
    cpu_model: str
    cpu_count: int
    gpu_model: str
    vram: int
    ram: int
    power_limit: Optional[int]
    network_download_speed: float
    network_upload_speed: float
    operating_system: str
    gpu_count: Optional[int]
    version: Optional[str] = None


@dataclass
class NodeInfo:
    node_id: UUID
    name: str
    name_alias: str
    created_at: datetime
    specs: Optional[NodeSpecs]


@dataclass
class FullNodeInfo(NodeInfo):
    specs: NodeSpecs


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
    power_percent: Optional[int]


@dataclass
class NodeHealth:
    node_id: UUID
    cpu_percent: int
    ram_percent: int
    disk_percent: int
    gpus: List[NodeGPUHealth]


class ModelType(Enum):
    LLM = 1
    DIFFUSION = 2


@dataclass
class ConnectedNode:
    uid: UUID
    user_id: UUID
    model: str
    vram: int
    connected_at: int  # in seconds
    connected_host: BackendHost
    websocket: WebSocket
    request_incoming_queues: Dict[str, asyncio.Queue]
    node_status: NodeStatus
    model_type: ModelType = ModelType.LLM
    is_self_hosted: bool = False
    version: Optional[Version] = None

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


# The websocket request for image generations and edits
class ImageGenerationWebsocketRequest(BaseModel):
    request_id: str = Field(description="A unique identifier for the request")
    prompt: str = Field(description="Prompt for the image generation")
    image: Optional[str] = Field(description="Base64 encoded image as input")
    n: int = Field(description="Number of images to generate")
    size: Optional[str] = Field(description="The size of the generated images.")


class ImageGenerationWebsocketResponse(BaseModel):
    node_id: UUID = Field(description="The node ID that processed the request")
    request_id: str = Field(description="Unique ID for the request")
    images: List[str] = Field(description="Base64 encoded images as output")
    error: Optional[str] = Field(description="Error message if the request failed")
