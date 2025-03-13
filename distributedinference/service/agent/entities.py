from datetime import datetime
from typing import Literal
from typing import Optional
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
    docker_image_hash: str = Field(description="Docker image hash")
    pcr0_hash: str = Field(description="PCR0")
    metadata: Optional[Dict] = Field(default=None, description="Agent configuration")


class GetAgentRequest(BaseModel):
    agent_id: UUID = Field(description="Agent ID")


class GetAgentResponse(ApiResponse, Agent):
    pass


class GetAgentsResponse(ApiResponse):
    agents: List[Agent] = Field(description="Agents")


class CreateAgentRequest(BaseModel):
    name: str = Field(description="Name")
    docker_image: str = Field(description="Docker image")
    docker_image_hash: str = Field(description="Docker image hash")
    env_vars: Dict[str, Any] = Field(description="Environment variables")


class CreateAgentResponse(ApiResponse):
    agent_id: UUID = Field(description="Agent ID")


class UpdateAgentRequest(BaseModel):
    name: str = Field(description="Name")
    docker_image: str = Field(description="Docker image")
    docker_image_hash: str = Field(description="Docker image hash")
    env_vars: Dict[str, Any] = Field(description="Environment variables")


class UpdateAgentResponse(ApiResponse):
    pass


class UpdateAgentMetadataRequest(BaseModel):
    description: str = Field(
        description="Agent description",
        max_length=2000,
    )
    client_url: str = Field(
        description="Link to a page where the agent can be accessed",
        max_length=1000,
    )


class UpdateAgentMetadataResponse(ApiResponse):
    pass


class DeleteAgentResponse(ApiResponse):
    pass


SUPPORTED_LOG_LEVELS_TYPE = Literal[
    "debug",
    "info",
    "warning",
    "warn",
    "error",
    "fatal",
    "critical",
    "thought",
]
SUPPORTED_LOG_LEVEL_STANDALONE: SUPPORTED_LOG_LEVELS_TYPE = "thought"
SUPPORTED_LOG_LEVELS: List[SUPPORTED_LOG_LEVELS_TYPE] = [
    "debug",
    "info",
    "warning",
    "warn",
    "error",
    "fatal",
    "critical",
    SUPPORTED_LOG_LEVEL_STANDALONE,
]


class Log(BaseModel):
    # TODO: pick some reasonable length?
    text: str = Field(description="Log content", max_length=5000)
    level: str = Field(
        description='Log level, possible options: debug, info, warning, critical, error or special case "thought", '
        'defaults to "info" on an invalid value'
    )
    timestamp: int = Field(description="Log creation timestamp in seconds")
    signature: Optional[str] = Field(
        description="Log signature, signed by TEE", default=None
    )


class AddLogsRequest(BaseModel):
    agent_instance_id: UUID = Field(description="Agent instance ID")
    logs: List[Log] = Field(
        description="Agent logs",
        max_length=20,
    )


class AddLogsResponse(ApiResponse):
    pass


class GetLogsRequest(BaseModel):
    agent_id: UUID = Field(description="Agent ID")
    limit: Optional[int] = Field(
        description="List of verified chat completions.", default=50
    )
    level: Optional[SUPPORTED_LOG_LEVELS_TYPE] = Field()
    cursor: Optional[UUID] = Field(description="Cursor for pagination.", default=None)


class GetLogsResponse(ApiResponse):
    logs: List[Log] = Field(description="Agent logs")
    cursor: Optional[UUID] = Field(
        description="Cursor for pagination.",
    )
