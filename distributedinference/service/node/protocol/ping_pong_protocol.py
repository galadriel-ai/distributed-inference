import time
import uuid
from typing import Any

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict
from starlette.websockets import WebSocket

import settings
from distributedinference import api_logger
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.node.protocol.entities import (
    PingRequest,
    PingPongMessageType,
)

logger = api_logger.get()


# NodePingInfo class to store the information of a active node
# TODO: SOme of the state info needs to be persisted in DB
class NodePingInfo(BaseModel):
    websocket: WebSocket
    rtt: float = 0  # the last rtt of the node
    next_ping_time: float = 0  # the scheduled time to send the bext ping to the node
    ping_streak: int = 0  # no of consecutive pings that the node has responded to
    miss_streak: int = 0  # no of consecutive pings that the node has missed
    waiting_for_pong: bool = False  # flag to check if the node is waiting for pong
    last_ping_nonce: str = (
        ""  # the nonce of the last ping sent to the node to avoid replay attacks
    )
    last_ping_sent_time: float = 0  # the time when the last ping was sent to the node

    model_config = ConfigDict(arbitrary_types_allowed=True)


class PingPongProtocol:
    def __init__(self, node_repository: NodeRepository):
        self.node_repository = (
            node_repository  # TODO: Will be used to RTT in the NodeInfo table
        )

        self.active_nodes = {}
        logger.info(f"{settings.PING_PONG_PROTOCOL_NAME}: Protocol initialized")

    # Handle the responses from the client
    async def handle(self, data: Any):
        node_id = data.node_id
        node_info = self.active_nodes[node_id]
        if node_info.waiting_for_pong:
            if data.nonce != node_info.last_ping_nonce:
                logger.warning(
                    f"{settings.PING_PONG_PROTOCOL_NAME}: Received pong with invalid nonce from node {node_id}, expected {node_info.last_ping_nonce}, got {data.nonce}"
                )
                return
            await self.got_pong_on_time(node_id, node_info)
        else:
            logger.warning(
                f"{settings.PING_PONG_PROTOCOL_NAME}: Received unexpected pong from node {node_id}"
            )

    # Regularly check if we have received the pong responses and to send ping messages
    async def job(self):
        await self.send_pings()
        await self.check_for_pongs()

    # Add a node to the active nodes dictionary
    # called when a new node connects to the server through websocket
    def add_node(self, node_id, websocket: WebSocket) -> bool:
        if node_id in self.active_nodes:
            logger.warning(
                f"{settings.PING_PONG_PROTOCOL_NAME}: Node {node_id} already exists in the active nodes"
            )
            return False
        current_time = _current_milli_time()
        self.active_nodes[node_id] = NodePingInfo(
            websocket=websocket,
            rtt=0,
            next_ping_time=current_time + (settings.PING_INTERVAL_IN_SECONDS * 1000),
            ping_streak=0,
            miss_streak=0,
            waiting_for_pong=False,
            last_ping_nonce="",
            last_ping_sent_time=current_time,
        )
        logger.info(
            f"{settings.PING_PONG_PROTOCOL_NAME}: Node {node_id} has been added to the active nodes"
        )
        return True

    # Remove a node from the active nodes dictionary
    # called when a node disconnects the websocket from the server
    def remove_node(self, node_id) -> bool:
        if node_id not in self.active_nodes:
            logger.warning(
                f"{settings.PING_PONG_PROTOCOL_NAME}: Node {node_id} does not exist in the active nodes"
            )
            return False

        del self.active_nodes[node_id]
        logger.info(
            f"{settings.PING_PONG_PROTOCOL_NAME}: Node {node_id} has been deleted from the active nodes"
        )
        return True

    async def send_pings(self):
        current_time = _current_milli_time()
        for node_id, node_info in self.active_nodes.items():
            if current_time > node_info.next_ping_time:
                if not node_info.waiting_for_pong:
                    await self.send_ping_message(node_id)

    async def check_for_pongs(self):
        for node_id, node_info in self.active_nodes.items():
            if node_info.waiting_for_pong:  # waiting for pong
                if round(_current_milli_time() - node_info.last_ping_sent_time) > (
                    (settings.PING_TIMEOUT_IN_SECONDS * 1000)
                ):
                    await self.missed_pong(
                        node_id, node_info
                    )  # timed out, mark it as missed pong

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
            nonce=node_info.last_ping_nonce,
            timestamp=node_info.last_ping_sent_time,
            response_timeout=settings.PING_TIMEOUT_IN_SECONDS * 1000,
        )
        websocket = self.active_nodes[node_id].websocket
        data = jsonable_encoder(ping_request)
        message = {"protocol": settings.PING_PONG_PROTOCOL_NAME, "data": data}
        await websocket.send_json(message)
        logger.info(
            f"{settings.PING_PONG_PROTOCOL_NAME}: Sent ping to node {node_id}, with nonce {node_info.last_ping_nonce}"
        )

    async def missed_pong(self, node_id, node_info):
        if node_info.miss_streak == 0:  # first miss
            node_info.ping_streak = 0  # reset the ping streak
        node_info.miss_streak += 1
        node_info.waiting_for_pong = False  # reset the waiting for pong flag
        if node_info.miss_streak > 3:
            self.remove_node(
                node_id
            )  # remove the node from the active nodes if it has missed 3 pongs consecutively
            logger.error(
                f"{settings.PING_PONG_PROTOCOL_NAME}: Node {node_id} has been removed due to too many missed pongs"
            )
        else:
            logger.error(
                f"{settings.PING_PONG_PROTOCOL_NAME}: Missed pong from node {node_id}, with nonce {node_info.last_ping_nonce}"
            )

    async def got_pong_on_time(self, node_id, node_info):
        # Got the right pong response
        node_info.next_ping_time = _current_milli_time() + (
            settings.PING_INTERVAL_IN_SECONDS * 1000
        )  # set the next ping time  # set the next ping time
        node_info.waiting_for_pong = False  # reset the waiting for pong flag
        node_info.miss_streak = 0  # resset miss streak if any
        node_info.ping_streak += 1  # increment the ping streak
        node_info.rtt = (
            _current_milli_time() - node_info.last_ping_sent_time
        )  # calculate the rtt
        logger.info(
            f"{settings.PING_PONG_PROTOCOL_NAME}: Received pong from node {node_id}, with nonce {node_info.last_ping_nonce} with rtt {node_info.rtt} in msec"
        )


def _current_milli_time():
    return round(time.time() * 1000)
