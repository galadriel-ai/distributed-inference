from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field

from distributedinference.service.entities import ApiResponse


class CreateNodeRequest(BaseModel):
    node_name: str = Field(description="User defined node name")


class CreateNodeResponse(ApiResponse):
    node_id: str = Field(description="Unique ID of the Node")


class UpdateNodeRequest(BaseModel):
    node_id: str = Field(description="Unique ID of the Node")
    node_name: Optional[str] = Field(
        description="User defined node name to use as the new value",
        min_length=3,
        max_length=40,
        default=None,
    )
    is_archived: Optional[bool] = Field(
        description="New node archival status",
        default=None,
    )


class UpdateNodeResponse(BaseModel):
    is_name_updated: bool = Field(description="Shows if the name was updated")
    is_archival_status_updated: bool = Field(
        description="Shows if the archival status was updated"
    )


class NodeInfoRequest(BaseModel):
    node_id: str = Field(description="Unique ID of the Node")
    gpu_model: Optional[str] = Field(description="GPU model", default=None)
    vram: Optional[int] = Field(description="VRAM in MB", default=None)
    gpu_count: Optional[int] = Field(description="GPU count", default=None)
    cpu_model: Optional[str] = Field(description="CPU model", default=None)
    cpu_count: Optional[int] = Field(description="CPU cores count", default=None)
    ram: Optional[int] = Field(description="RAM in MB", default=None)
    network_download_speed: Optional[float] = Field(
        description="Network download speed in Mbps", default=None
    )
    network_upload_speed: Optional[float] = Field(
        description="Network upload speed in Mbps", default=None
    )
    operating_system: Optional[str] = Field(description="Operating system")
    version: Optional[str] = Field(description="Node version", default=None)


class ListNodeRequestNode(NodeInfoRequest):
    name_alias: str = Field(description="User defined name for the Node")
    status: str = Field(description="Node status")
    run_duration_seconds: int = Field(
        description="Run duration in seconds since connecting", default=0
    )
    total_uptime_seconds: Optional[int] = Field(
        description="Node total uptime in seconds", default=None
    )
    requests_served: int = Field(
        description="Total inference requests served by the node", default=0
    )
    requests_served_day: int = Field(
        description="Total inference requests served by the node past 24 hours",
        default=0,
    )
    benchmark_tokens_per_second: Optional[float] = Field(
        description="Theoretical max tokens per second for the node"
    )
    is_archived: bool = Field(description="true if a node is archived")
    node_created_at: int = Field(
        description="UNIX timestamp of node first registration"
    )


class ListNodeResponse(ApiResponse):
    nodes: List[ListNodeRequestNode] = Field(description="User nodes")


class GetNodeInfoResponse(NodeInfoRequest):
    name_alias: str = Field(description="User defined name for the node")
    status: str = Field(description="Node status")
    run_duration_seconds: Optional[int] = Field(
        description="Run duration in seconds since connecting", default=None
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
        description="Total inference requests served by the node", default=0
    )
    requests_served_day: int = Field(
        description="Total inference requests served by the node past 24 hours",
        default=0,
    )
    average_time_to_first_token: Optional[float] = Field(
        description="Average time to first token for the node", default=0
    )

    benchmark_tokens_per_second: Optional[float] = Field(
        description="Node benchmark generated tokens per second", default=0
    )
    benchmark_model_name: Optional[str] = Field(
        description="Node benchmark model name", default=None
    )
    benchmark_created_at: Optional[int] = Field(
        description="UNIX timestamp of node benchmark creation", default=0
    )

    completed_inferences: List[InferenceStats] = Field(
        description="Last 10 processed inference calls", default=[]
    )


class GetUserAggregatedStatsResponse(BaseModel):
    total_requests_served: Optional[int] = Field(
        description="User total requests served"
    )
    requests_served_day: Optional[int] = Field(
        description="User total requests served in the past 24h"
    )
    average_time_to_first_token: Optional[float] = Field(
        description="User average time to first token across all their nodes"
    )
    benchmark_total_tokens_per_second: Optional[float] = Field(
        description="User max theoretical tokens per second across all their nodes"
    )


class PostNodeInfoRequest(NodeInfoRequest):
    pass


class PostNodeInfoResponse(ApiResponse):
    pass


class NodeBenchmarkRequest(BaseModel):
    node_id: str = Field(description="Unique ID of the Node")
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
