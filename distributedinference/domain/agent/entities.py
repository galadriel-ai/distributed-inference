from datetime import datetime
from dataclasses import dataclass
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from uuid import UUID


@dataclass
class Agent:
    id: UUID
    name: str
    created_at: datetime
    docker_image: str
    docker_image_hash: str
    env_vars: Dict[str, Any]
    last_updated_at: datetime
    user_profile_id: UUID


@dataclass
class AgentInstance:
    id: UUID
    agent_id: UUID
    tee_host_base_url: str
    enclave_cid: str
    instance_env_vars: Dict[str, Any]
    pcr0: Optional[str]
    created_at: datetime
    last_updated_at: datetime


@dataclass
class Attestation:
    id: UUID
    agent_instance_id: UUID
    attestation: str
    valid_from: datetime
    valid_to: datetime
    created_at: datetime
    last_updated_at: datetime


@dataclass
class AttestationDetails:
    attestation: str
    valid_from: datetime
    valid_to: datetime
    pcr0: str


@dataclass
class CreateAgentInput:
    user_id: UUID
    name: str
    docker_image: str
    docker_image_hash: str
    env_vars: Dict[str, Any]


@dataclass
class CreateAgentOutput:
    agent: Agent


@dataclass
class UpdateAgentInput:
    agent_id: UUID
    name: str
    docker_image: str
    docker_image_hash: str
    env_vars: Dict[str, Any]


@dataclass
class AgentLog:
    text: str
    level: str
    timestamp: int
    signature: Optional[str]


@dataclass
class AgentLogInput:
    agent_id: UUID
    agent_instance_id: UUID
    logs: List[AgentLog]


@dataclass
class GetAgentLogsInput:
    agent_id: UUID
    limit: int
    levels: List[str]
    cursor: Optional[UUID]


@dataclass
class AgentLogOutput(AgentLog):
    id: UUID


@dataclass
class GetAgentLogsOutput:
    logs: List[AgentLogOutput]
    cursor: Optional[UUID]


@dataclass
class DeployedAgent:
    id: UUID
    name: str
    docker_image: str
    created_at: datetime


@dataclass
class AllAgentsOutput:
    agents: List[DeployedAgent]
    cursor: Optional[UUID]


@dataclass
class ExplorerAgentInstance:
    id: UUID
    enclave_cid: str
    is_deleted: bool
    pcr0: Optional[str]
    attestation: Optional[str]
    created_at: datetime


@dataclass
class DeployedAgentDetails(DeployedAgent):
    agent_instances: List[ExplorerAgentInstance]


@dataclass
class AgentExplorerOutput:
    agent_count: int
    node_count: int
    uptime_24h: int

    latest_agents: List[DeployedAgent]
