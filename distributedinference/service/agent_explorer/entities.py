from typing import List
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field

from distributedinference.service.entities import ApiResponse


class DeployedAgentInstance(BaseModel):
    instance_id: UUID = Field(description="Agent instance ID")
    name: str = Field(description="Agent instance name")
    docker_image: str = Field(description="Docker image name")
    created_at: int = Field(description="UNIX timestamp of the agent instance creation")


class AgentExplorerResponse(ApiResponse):
    agent_count: int = Field(description="Total agent count in the network")
    node_count: int = Field(description="Total nodes count in the network")
    uptime_24h: int = Field(description="24h uptime in percentage (2 decimals)")
    latest_instances: List[DeployedAgentInstance] = Field(
        description="Latest deployed agent instances"
    )
