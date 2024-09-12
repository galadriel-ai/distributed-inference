from typing import List
from typing import Literal
from typing import Optional

from pydantic import BaseModel
from pydantic import Field

from distributedinference.service.entities import ApiResponse


class NodeInfoRequest(BaseModel):
    gpu_model: Optional[str] = Field(description="GPU model", default=None)
    vram: Optional[int] = Field(description="VRAM in MB", default=None)
    cpu_model: str = Field(description="CPU model")
    cpu_count: int = Field(description="CPU cores count")
    ram: int = Field(description="RAM in MB")
    network_download_speed: float = Field(
        description="Network download speed in Mbps", default=None
    )
    network_upload_speed: float = Field(
        description="Network upload speed in Mbps", default=None
    )
    operating_system: str = Field(description="Operating system")


class GetNodeInfoResponse(NodeInfoRequest):
    status: Literal["online", "offline"] = Field(description="Node status")
    run_duration_seconds: int = Field(
        description="Run duration in seconds since connecting"
    )
    node_created_at: int = Field(
        description="UNIX timestamp of node first registration"
    )


class InferenceStats(BaseModel):
    model_name: str = Field(description="Model name for the given inference")
    prompt_tokens: int = Field(description="Prompt tokens count")
    completion_tokens: int = Field(description="Completion tokens count")
    total_tokens: int = Field(description="Total tokens count")
    created_at: int = Field(description="UNIX timestamp of the inference completion")


class GetNodeStatsResponse(BaseModel):
    requests_served: int = Field(
        description="Total inference requests served by the node"
    )
    average_time_to_first_token: Optional[float] = Field(
        description="Average time to first token for the node"
    )

    benchmark_tokens_per_second: Optional[float] = Field(
        description="Node benchmark generated tokens per second"
    )
    benchmark_model_name: Optional[str] = Field(description="Node benchmark model name")
    benchmark_created_at: Optional[int] = Field(
        description="UNIX timestamp of node benchmark creation"
    )

    completed_inferences: List[InferenceStats] = Field(
        description="Last 10 processed inference calls"
    )


class PostNodeInfoRequest(NodeInfoRequest):
    pass


class PostNodeInfoResponse(ApiResponse):
    pass


class NodeBenchmarkRequest(BaseModel):
    model_name: str = Field(description="Model name")
    tokens_per_second: float = Field(description="Tokens per second")

    # pylint: disable=R0903
    class Config:
        # to allow `model_name` field without warnings
        protected_namespaces = ()


class GetNodeBenchmarkResponse(NodeBenchmarkRequest):
    pass


class PostNodeBenchmarkRequest(NodeBenchmarkRequest):
    pass


class PostNodeBenchmarkResponse(ApiResponse):
    pass
