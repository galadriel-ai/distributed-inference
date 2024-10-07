import asyncio
from typing import Any
from typing import Dict

from fastapi import status
from fastapi.exceptions import WebSocketException

import settings
from distributedinference import api_logger
from distributedinference.repository.metrics_queue_repository import (
    MetricsQueueRepository,
)
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

    # Give the parsed data to the respective protocol
    async def handle(self, parsed_data: Any):
        protocol_name = parsed_data.get("protocol")
        protocol_data = parsed_data.get("data")
        if protocol_name is None or protocol_data is None:
            raise WebSocketException(
                code=status.WS_1002_PROTOCOL_ERROR,
                reason="Invalid protocol name or data",
            )
        if protocol_name in self.protocols:
            proto = self.protocols[protocol_name]
            await proto.handle(protocol_data)
        else:
            raise WebSocketException(
                code=status.WS_1002_PROTOCOL_ERROR,
                reason=f"Invalid protocol name {protocol_name}",
            )

    # Give a chance to run protocol jobs every PROTOCOL_RESPONSE_CHECK_INTERVAL_IN_SECONDS seconds
    async def run(self):
        for protocol in self.protocols.values():
            await protocol.run()


async def execute(
    protocol_handler: ProtocolHandler,
    metrics_queue_repository: MetricsQueueRepository,
) -> None:
    try:
        logger.info("Started Protocol Handler")

        # Instantiate and Register the protocols
        for protocol_name, config in settings.GALADRIEL_PROTOCOL_CONFIG.items():
            if protocol_name == settings.PING_PONG_PROTOCOL_NAME:
                ping_pong_protocol = PingPongProtocol(
                    metrics_queue_repository, protocol_name, config
                )
                protocol_handler.register(protocol_name, ping_pong_protocol)

        while True:
            # trigger protocol runs every PROTOCOL_RESPONSE_CHECK_INTERVAL_IN_SECONDS seconds
            await asyncio.sleep(settings.PROTOCOL_RESPONSE_CHECK_INTERVAL_IN_SECONDS)
            await protocol_handler.run()
    except Exception:
        logger.error(
            "Failed to while running protocol handler",
            exc_info=True,
        )
