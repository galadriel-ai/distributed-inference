from enum import Enum

from pydantic import BaseModel
from pydantic import Field


class PingPongMessageType(Enum):
    PING = 1
    PONG = 2


class PingRequest(BaseModel):
    protocol_version: str = Field(
        description="Protocol version of the ping-pong protocol"
    )
    message_type: PingPongMessageType = Field(description="Message type")
    nonce: str = Field(description="A random number to prevent replay attacks")
    timestamp: int = Field(description="Timestamp of the request in milliseconds")
    response_timeout: int = Field(
        description="Number of milliseconds the client has to respond to the ping"
    )


class PingResponse(BaseModel):
    protocol_version: str = Field(
        description="Protocol version of the ping-pong protocol"
    )
    message_type: PingPongMessageType = Field(description="Message type")
    nonce: str = Field(description="The same nonce as in the request")
