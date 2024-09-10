from typing import Dict
from pydantic import BaseModel
from pydantic import Field


class NetworkStatsResponse(BaseModel):
    nodes_count: int = Field(description="Total registered nodes count")
    connected_nodes_count: int = Field(description="Currently connected nodes count")
    network_throughput: str = Field(
        description="Current network throughput in tokens/second"
    )
    network_throughput_by_model: Dict = Field(
        description="Current network throughput per model in tokens/second"
    )
