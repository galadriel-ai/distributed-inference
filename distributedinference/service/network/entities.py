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
    inference_count_day: int = Field(
        description="Inferences count in the past 24 hours"
    )
    network_models_stats: List[NetworkModelStats] = Field(
        description="Current network throughput per model in tokens/second"
    )


class UserApiKey(BaseModel):
    api_key_prefix: str = Field(description="Partially revealed API key")
    created_at: str = Field(description="API key creation date in ISO 8601 format.")


class GetApiKeysResponse(BaseModel):
    api_keys: List[UserApiKey] = Field(description="User API keys")


class CreateApiKeyResponse(BaseModel):
    api_key: str = Field(description="Newly created API key")
    created_at: str = Field(description="API key creation date in ISO 8601 format.")
