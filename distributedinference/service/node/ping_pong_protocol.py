import time
import uuid
from typing import Any
from fastapi import WebSocket  # or 
from distributedinference import api_logger, settings
from distributedinference.service.node.protocol_handler import ProtocolHandler, BaseProtocol  
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.domain.node.entities import NodePingInfo, PingRequest, PingPongMessageType


logger = api_logger.get()


class PingPongProtocol(BaseProtocol):
    def __init__(self, node_repository: NodeRepository, protocol_handler: ProtocolHandler):
        self.active_nodes = {}  
        super().__init__(protocol_handler)
        logger.info(f"{settings.PING_PONG_PROTOCOL_NAME}: Protocol initialized")

    # Implement abstract method from the base class
    async def handler(self,data: Any, websocket: WebSocket):
        node_id = data.node_id
        node_info = self.active_nodes[node_id]
        node_info.waiting_for_pong = False
        node_info.miss_streak = 0
        node_info.ping_streak += 1
        node_info.rtt = _current_milli_time() - node_info.last_ping_time
        logger.info(f"{settings.PING_PONG_PROTOCOL_NAME}: Received pong from node {node_id}, with nonce {node_info.nonce} with rtt {node_info.rtt}")
        
    # Implement abstract method from the base class    
    async def job(self):
        await self.check_for_response()
        await self.send_pings()
        
    # Add a node to the active nodes dictionary
    def add_node(self, node_id, websocket: WebSocket):
        current_time = _current_milli_time()
        self.active_nodes[node_id] = NodePingInfo(
            websocket=websocket, 
            rtt=0,
            next_ping_time=current_time + settings.PING_INTERVAL,
            ping_streak=0,
            miss_streak=0,
            waiting_for_pong=False,
            last_ping_nonce=None,   
            last_ping_time=current_time)
        logger.info(f"{settings.PING_PONG_PROTOCOL_NAME}: Node {node_id} has been added to the active nodes")

    def remove_node(self, node_id):
        if node_id in self.active_nodes:
            del self.active_nodes[node_id]
            logger.info(f"{settings.PING_PONG_PROTOCOL_NAME}: Node {node_id} has been deleted from the active nodes")

    async def send_pings(self):                    
        nodes_to_ping = await self.get_next_nodes_to_ping()
        for node_id in nodes_to_ping:
            node_info = self.active_nodes[node_id]
            node_info.waiting_for_pong = True # set the node to waiting for pong        
            node_info.last_ping_time = _current_milli_time() # update the last ping time
            node_info.last_ping_nonce = str(uuid.uuid4()) # generate a new nonce
            await self.send_ping_message(node_id, node_info.last_ping_nonce)
            logger.info(f"{settings.PING_PONG_PROTOCOL_NAME}: Sent ping to node {node_id}")
            
    async def check_for_response(self):
        for node_id, node_info in self.active_nodes.items():
            if node_info.waiting_for_pong:
                if _current_milli_time() - node_info.last_ping_time > self.ping_timeout:
                    node_info.miss_streak += 1  
                    node_info.waiting_for_pong = False
                    if node_info.miss_streak > 3:
                        self.remove_node(node_id) # remove the node from the active nodes
                        logger.error(f"{settings.PING_PONG_PROTOCOL_NAME}: Node {node_id} has been removed due to too many missed pongs")
                        
    async def get_next_nodes_to_ping(self):
        current_time = _current_milli_time        
        nodes_to_ping = []
        for node_id, node_info in self.active_nodes.items():            
            if current_time > node_info.next_ping_time:                
                if not node_info.waiting_for_pong:
                    nodes_to_ping.append(node_id)                   
        return nodes_to_ping

    


    # Send a ping message to the client
    async def send_ping_message(self, node_id, nonce: str):        
        ping_request = PingRequest(
            protocol_version=settings.PING_PONG_PROTOCOL_VERSION,
            message_type=PingPongMessageType.PING,
            nonce=nonce,
            timestamp=_current_milli_time(),
            response_timeout=settings.PING_TIMEOUT
        )
        websocket = self.active_nodes[node_id].websocket
        await self.protocol_handler.send_message(settings.PING_PONG_PROTOCOL_NAME, ping_request, websocket)
        logger.info(f"{settings.PING_PONG_PROTOCOL_NAME}: Sent ping to node {node_id}, with nonce {nonce}")

def _current_milli_time():
    return round(time.time() * 1000)