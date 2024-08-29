from typing import Optional

from pydantic import BaseModel
from pydantic import Field

from distributedinference.service.entities import ApiResponse


class NodeInfoRequest(BaseModel):
    gpu_model: Optional[str] = Field(description="GPU model", default=None)
    vram: Optional[int] = Field(description="VRAM in MB", default=None)
    cpu_model: str = Field(description="CPU model")
    ram: int = Field(description="RAM in GB")
    network_speed: int = Field(description="Network speed in Mbps", default=None)
    operating_system: str = Field(description="Operating system")


class NodeInfoResponse(ApiResponse):
    pass
