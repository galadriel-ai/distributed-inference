import asyncio
from typing import Any
from typing import Dict

from fastapi import status
from fastapi.exceptions import WebSocketException

import settings
from distributedinference import api_logger
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.node.protocol.ping_pong_protocol import (
    PingPongProtocol,
)

logger = api_logger.get()


# Handler for all the protocols
class ProtocolHandler:
    def __init__(self):
        self.protocols: Dict[str, Any] = {}

    def register(self, protocol_name: str, protocol: Any):
        self.protocols[protocol_name] = protocol

    def deregister(self, protocol_name: str):
        if protocol_name in self.protocols:
            del self.protocols[protocol_name]

    def get(self, protocol_name: str) -> Any:
        return self.protocols.get(protocol_name)

    async def handle(self, protocol_name: str, data: Any):
        if protocol_name in self.protocols:
            proto = self.protocols[protocol_name]
            await proto.handler(data)
        else:
            raise WebSocketException(
                code=status.WS_1002_PROTOCOL_ERROR,
                reason=f"Invalid protocol name {protocol_name}",
            )


async def execute(
    protocol_handler: ProtocolHandler,
    node_repository: NodeRepository,
) -> None:
    try:
        logger.info("Started Protocol Handler")

        # Instantiate and Register the ping-pong protocol
        ping_pong_protocol = PingPongProtocol(node_repository)
        protocol_handler.register(settings.PING_PONG_PROTOCOL_NAME, ping_pong_protocol)

        # trigger protocol jobs every X seconds
        while True:
            await asyncio.sleep(settings.PROTOCOL_RESPONSE_CHECK_INTERVAL_IN_SECONDS)
            await ping_pong_protocol.job()
    except Exception:
        logger.error(
            "Failed to while running protocol handler",
            exc_info=True,
        )
