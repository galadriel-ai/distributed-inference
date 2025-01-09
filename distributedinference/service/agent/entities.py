from datetime import datetime
from uuid import UUID
from typing import Any
from typing import Dict
from typing import List

from pydantic import BaseModel
from pydantic import Field

from distributedinference.service.entities import ApiResponse


class Agent(BaseModel):
    agent_id: UUID = Field(description="Agent ID")
    name: str = Field(description="Name")
    updated_at: datetime = Field(description="Updated at")
    docker_image: str = Field(description="Docker image")
    pcr0_hash: str = Field(description="PCR0")


class GetAgentRequest(BaseModel):
    agent_id: UUID = Field(description="Agent ID")


class GetAgentResponse(ApiResponse, Agent):
    pass


class GetAgentsResponse(ApiResponse):
    agents: List[Agent] = Field(description="Agents")


class CreateAgentRequest(BaseModel):
    name: str = Field(description="Name")
    docker_image: str = Field(description="Docker image")
    env_vars: Dict[str, Any] = Field(description="Environment variables")


class CreateAgentResponse(ApiResponse):
    agent_id: UUID = Field(description="Agent ID")


class UpdateAgentRequest(BaseModel):
    name: str = Field(description="Name")
    docker_image: str = Field(description="Docker image")
    env_vars: Dict[str, Any] = Field(description="Environment variables")


class UpdateAgentResponse(ApiResponse):
    pass


class DeleteAgentResponse(ApiResponse):
    pass
