import time
import uuid
from typing import Any

from fastapi import WebSocket  # or
from pydantic import BaseModel
from pydantic import Field

import settings
from distributedinference import api_logger
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.node.protocol.entities import (
    PingRequest,
    PingPongMessageType,
)

logger = api_logger.get()


class NodePingInfo(BaseModel):
    websocket: WebSocket
    rtt: float = Field(
        default=0.0, description="Round-trip time of the last ping in milli seconds"
    )
    next_ping_time: float = Field(
        default=0.0, description="Timestamp of the next ping to be sent in milliseconds"
    )
    ping_streak: int = Field(
        default=0, description="Number of pings that received pongs consecutively"
    )
    miss_streak: int = Field(
        default=0,
        description="Number of pings that has not received a pong response consecutively",
    )
    # The following fields are used to store the intermediary state of the ping-pong protocol
    waiting_for_pong: bool = Field(
        default=False, description="Whether the node is waiting for a pong response"
    )
    last_ping_nonce: str = Field(default=None, description="Nonce of the last ping")
    last_ping_sent_time: float = Field(
        default_factory=time.time, description="Timestamp of the last ping"
    )


class PingPongProtocol:
    def __init__(self, node_repository: NodeRepository):
        self.node_repository = (
            node_repository  # TODO: Will be used to RTT in the NodeInfo table
        )
        self.active_nodes = {}
        logger.info(f"{settings.PING_PONG_PROTOCOL_NAME}: Protocol initialized")

    # Implement abstract method from the base class
    async def handler(self, data: Any):
        node_id = data.node_id
        node_info = self.active_nodes[node_id]
        if node_info.waiting_for_pong:
            if data.nonce != node_info.last_ping_nonce:
                logger.warning(
                    f"{settings.PING_PONG_PROTOCOL_NAME}: Received pong with invalid nonce from node {node_id}, expected {node_info.last_ping_nonce}, got {data.nonce}"
                )
                return
        await self.got_pong_on_time(node_id, node_info)

    # Implement abstract method from the base class
    async def job(self):
        await self.check_for_pongs()
        await self.send_pings()

    # Add a node to the active nodes dictionary
    # called when a new node connects to the server through websocket
    async def add_node(self, node_id, websocket: WebSocket):
        current_time = _current_milli_time()
        self.active_nodes[node_id] = NodePingInfo(
            websocket=websocket,
            rtt=0,
            next_ping_time=current_time + settings.PING_INTERVAL,
            ping_streak=0,
            miss_streak=0,
            waiting_for_pong=False,
            last_ping_nonce=None,
            last_ping_sent_time=current_time,
        )
        logger.info(
            f"{settings.PING_PONG_PROTOCOL_NAME}: Node {node_id} has been added to the active nodes"
        )

    # Remove a node from the active nodes dictionary
    # called when a node disconnects the websocket from the server
    async def remove_node(self, node_id):
        if node_id in self.active_nodes:
            del self.active_nodes[node_id]
            logger.info(
                f"{settings.PING_PONG_PROTOCOL_NAME}: Node {node_id} has been deleted from the active nodes"
            )

    async def send_pings(self):
        nodes_to_ping = await self.get_next_nodes_to_ping()
        for node_id in nodes_to_ping:
            node_info = self.active_nodes[node_id]
            if (
                node_info.waiting_for_pong is False
                and node_info.next_ping_time > _current_milli_time()
            ):
                await self.send_ping_message(node_id)

    async def check_for_pongs(self):
        for node_id, node_info in self.active_nodes.items():
            if node_info.waiting_for_pong:
                if (
                    _current_milli_time() - node_info.last_ping_sent_time
                    > settings.PING_INTERVAL
                ):
                    await self.missed_pong(node_id, node_info)

    async def get_next_nodes_to_ping(self):
        current_time = _current_milli_time()
        nodes_to_ping = []
        for node_id, node_info in self.active_nodes.items():
            if current_time > node_info.next_ping_time:
                if not node_info.waiting_for_pong:
                    nodes_to_ping.append(node_id)
        return nodes_to_ping

    # Send a ping message to the client
    async def send_ping_message(self, node_id):
        node_info = self.active_nodes[node_id]

        node_info.next_ping_time = 0  # reset the next ping time
        node_info.waiting_for_pong = True  # set the node to waiting for pong
        node_info.last_ping_sent_time = (
            _current_milli_time()
        )  # update the last ping time
        node_info.last_ping_nonce = str(uuid.uuid4())  # g

        ping_request = PingRequest(
            protocol_version=settings.PING_PONG_PROTOCOL_VERSION,
            message_type=PingPongMessageType.PING,
            nonce=node_info.nonce,
            timestamp=node_info.last_ping_sent_time,
            response_timeout=settings.PING_TIMEOUT,
        )
        websocket = self.active_nodes[node_id].websocket
        message = {"protocol": settings.PING_PONG_PROTOCOL_NAME, "data": ping_request}
        await websocket.send_json(message)
        logger.info(
            f"{settings.PING_PONG_PROTOCOL_NAME}: Sent ping to node {node_id}, with nonce {node_info.nonce}"
        )

    async def missed_pong(self, node_id, node_info):
        if node_info.miss_streak == 0:  # first miss
            node_info.ping_streak = 0  # reset the ping streak
        node_info.miss_streak += 1
        node_info.waiting_for_pong = False  # reset the waiting for pong flag
        if node_info.miss_streak > 3:
            await self.remove_node(
                node_id
            )  # remove the node from the active nodes if it has missed 3 pongs consecutively
            logger.error(
                f"{settings.PING_PONG_PROTOCOL_NAME}: Node {node_id} has been removed due to too many missed pongs"
            )
        else:
            logger.error(
                f"{settings.PING_PONG_PROTOCOL_NAME}: Missed pong from node {node_id}, with nonce {node_info.nonce}"
            )

    async def got_pong_on_time(self, node_id, node_info):
        # Got the right pong response
        node_info.next_ping_time = (
            _current_milli_time() + settings.PING_INTERVAL  # set the next ping time
        )  # set the next ping time
        node_info.waiting_for_pong = False  # reset the waiting for pong flag
        node_info.miss_streak = 0  # resset miss streak if any
        node_info.ping_streak += 1  # increment the ping streak
        node_info.rtt = (
            _current_milli_time() - node_info.last_ping_sent_time
        )  # calculate the rtt
        logger.info(
            f"{settings.PING_PONG_PROTOCOL_NAME}: Received pong from node {node_id}, with nonce {node_info.nonce} with rtt {node_info.rtt}"
        )


def _current_milli_time():
    return round(time.time() * 1000)
