from typing import Dict
from typing import List
from typing import Optional
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field

from distributedinference.service.entities import ApiResponse


class DeployedAgentModel(BaseModel):
    agent_id: UUID = Field(description="Agent instance ID")
    name: str = Field(description="Agent instance name")
    docker_image: str = Field(description="Docker image name")
    created_at: int = Field(description="UNIX timestamp of the agent creation")


class AgentExplorerResponse(ApiResponse):
    agent_count: int = Field(description="Total agent count in the network")
    node_count: int = Field(description="Total nodes count in the network")
    uptime_24h: int = Field(description="24h uptime in percentage (2 decimals)")
    latest_agents: List[DeployedAgentModel] = Field(
        description="Latest deployed agent instances"
    )


class AgentSearchResponse(ApiResponse):
    agents: List[DeployedAgentModel] = Field(
        description="Latest deployed agent instances"
    )


class AllAgentsResponse(ApiResponse):
    agents: List[DeployedAgentModel] = Field(
        description="Latest deployed agent instances"
    )
    cursor: Optional[str] = Field(description="Optional cursor for pagination")


class AgentInstanceModel(BaseModel):
    enclave_cid: str = Field(description="enclave CID")
    is_deleted: bool = Field(description="Shows if the instance was deleted")
    pcr0: Optional[str] = Field(description="Agent instance pcr0")
    attestation: Optional[str] = Field(
        description="Agent instance latest found attestation"
    )
    created_at: int = Field(description="UNIX timestamp of the agent instance creation")


class AgentDetailsResponse(ApiResponse):
    agent_id: UUID = Field(description="Agent ID")
    name: str = Field(description="Agent instance name")
    docker_image: str = Field(description="Docker image name")
    created_at: int = Field(description="UNIX timestamp of the agent instance creation")
    agent_instances: List[AgentInstanceModel] = Field(description="Agent instances")
    metadata: Dict = Field(description="Agent's configurable metadata")


class AgentAttestationResponse(ApiResponse):
    attestation: Optional[str] = Field(description="Agent attestation")
