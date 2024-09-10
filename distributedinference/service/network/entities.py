from typing import List

from pydantic import BaseModel
from pydantic import Field


class NetworkModelStats(BaseModel):
    model_name: str = Field(description="Model name")
    throughput: str = Field(description="Throughput in tokens/second")


class NetworkStatsResponse(BaseModel):
    nodes_count: int = Field(description="Total registered nodes count")
    connected_nodes_count: int = Field(description="Currently connected nodes count")
    network_throughput: str = Field(
        description="Current network throughput in tokens/second"
    )
    network_models_stats: List[NetworkModelStats] = Field(
        description="Current network throughput per model in tokens/second"
    )
