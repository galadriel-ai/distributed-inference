import asyncio  
from abc import abstractmethod
from typing import Dict, Callable, Any
from fastapi import WebSocket
from distributedinference import api_logger, settings
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.node.ping_pong_protocol import PingPongProtocol, BaseProtocol

logger = api_logger.get()


async def execute(
    node_repository: NodeRepository,    
) -> None:   
    try:            
        logger.debug("Running Protocol Handler")
        protocol_handler = ProtocolHandler()
        ping_pong_protocol = PingPongProtocol(node_repository, protocol_handler)
        protocol_handler.register(settings.PING_PONG_PROTOCOL_NAME, ping_pong_protocol.handler)
            
        while True:
            await asyncio.sleep(settings.PROTOCOL_RESPONSE_CHECK_INTERVAL)
            await ping_pong_protocol.check_for_response()
    except Exception:
        logger.error(
            f"Failed to initialize protocol handler",
            exc_info=True,
        )


# Protocol handlers
class ProtocolHandler:
    def __init__(self):
        self.protocols: Dict[str, BaseProtocol] = {}

    def register(self, protocol_name: str, protocol: BaseProtocol):
        self.protocols[protocol_name] = protocol
        
        
    async def handle(self, protocol: str, data: Any, websocket: WebSocket):
        if protocol in self.protocols:
            self.handlers[protocol](data, websocket)
        else:
            await websocket.send_text(f"Unknown protocol: {protocol}")


    # A generic function to send any protocol message to the client
    async def send_message(self, protocol_name: str, data: Any, websocket: WebSocket):
        message = {
            "protocol": protocol_name,
            "data": data
        }
        await websocket.send_json(message)
        

class BaseProtocol:
    def __init__(self, protocol_handler: ProtocolHandler):
        self.protocol_handler = protocol_handler

    @abstractmethod
    def handle(self, data: Any, websocket: WebSocket):
        # This method must be implemented by all protocols
        pass

        