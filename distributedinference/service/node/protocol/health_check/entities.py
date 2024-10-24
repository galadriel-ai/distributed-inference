from enum import Enum
from typing import List

from pydantic import BaseModel
from pydantic import Field


class HealthCheckMessageType(Enum):
    HEALTH_CHECK_REQUEST = 1
    HEALTH_CHECK_RESPONSE = 2


class HealthCheckRequest(BaseModel):
    protocol_version: str = Field(
        description="Protocol version of the health-check protocol"
    )
    message_type: HealthCheckMessageType = Field(
        description="Message type",
        default=HealthCheckMessageType.HEALTH_CHECK_REQUEST.value,
    )
    node_id: str = Field(description="Node ID")
    nonce: str = Field(description="A random number to prevent replay attacks")


class HealthCheckGPUUtilization(BaseModel):
    gpu_percent: int = Field(description="GPU utilization, percent")
    vram_percent: int = Field(description="VRAM utilization, percent")


class HealthCheckResponse(BaseModel):
    protocol_version: str = Field(
        description="Protocol version of the ping-pong protocol"
    )
    message_type: HealthCheckMessageType = Field(
        description="Message type",
        default=HealthCheckMessageType.HEALTH_CHECK_RESPONSE.value,
    )
    node_id: str = Field(description="Node ID")
    nonce: str = Field(description="The same nonce as in the request")

    cpu_percent: int = Field(description="CPU utilization, percent")
    ram_percent: int = Field(description="RAM utilization, percent")
    disk_percent: int = Field(description="Disk utilization, percent")
    gpus: List[HealthCheckGPUUtilization] = Field(description="GPU utilization")
