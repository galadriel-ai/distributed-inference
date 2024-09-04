from pydantic import BaseModel
from pydantic import Field


class NetworkStatsResponse(BaseModel):
    nodes_count: int = Field(description="Total registered nodes count")
    connected_nodes_count: int = Field(description="Currently connected nodes count")
    network_throughput: float = Field(
        description="Current network throughput in tokens/second"
    )
