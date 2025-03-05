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
    enclave_cid: str
    instance_env_vars: Dict[str, Any]
    created_at: datetime
    last_updated_at: datetime


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


@dataclass
class AgentLogInput:
    agent_id: UUID
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
class DeployedAgentDetails(DeployedAgent):
    is_deleted: bool


@dataclass
class AgentExplorerOutput:
    agent_count: int
    node_count: int
    uptime_24h: int

    latest_agents: List[DeployedAgent]
