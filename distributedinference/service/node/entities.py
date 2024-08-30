from typing import Optional

from pydantic import BaseModel
from pydantic import Field

from distributedinference.service.entities import ApiResponse


class NodeInfoRequest(BaseModel):
    gpu_model: Optional[str] = Field(description="GPU model", default=None)
    vram: Optional[int] = Field(description="VRAM in MB", default=None)
    cpu_model: str = Field(description="CPU model")
    cpu_count: int = Field(description="CPU cores count")
    ram: int = Field(description="RAM in MB")
    network_download_speed: int = Field(
        description="Network download speed in Mbps", default=None
    )
    network_upload_speed: int = Field(
        description="Network upload speed in Mbps", default=None
    )
    operating_system: str = Field(description="Operating system")


class GetNodeInfoResponse(NodeInfoRequest):
    pass


class PostNodeInfoRequest(NodeInfoRequest):
    pass


class PostNodeInfoResponse(ApiResponse):
    pass
