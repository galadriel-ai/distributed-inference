from datetime import datetime
from dataclasses import dataclass
from typing import Any
from typing import Dict
from uuid import UUID


@dataclass
class Agent:
    agent_id: UUID
    name: str
    created_at: datetime
    docker_image: str
    env_vars: Dict[str, Any]
    last_updated_at: datetime
    user_profile_id: UUID


@dataclass
class AgentInstance:
    agent_id: UUID
    instance_id: UUID
    created_at: datetime
    last_updated_at: datetime
    status: str


@dataclass
class CreateAgentInput:
    user_id: UUID
    name: str
    docker_image: str
    env_vars: Dict[str, Any]


@dataclass
class CreateAgentOutput:
    agent_id: UUID


@dataclass
class UpdateAgentInput:
    agent_id: UUID
    name: str
    docker_image: str
    env_vars: Dict[str, Any]
