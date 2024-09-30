import time
import uuid
from typing import Any
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict
from starlette.websockets import WebSocket

import settings
from distributedinference import api_logger
from distributedinference.domain.node.entities import NodeMetricsIncrement
from distributedinference.repository.metrics_queue_repository import (
    MetricsQueueRepository,
)
from distributedinference.service.node.protocol.entities import (
    PingRequest,
    PingPongMessageType,
    PongResponse,
)

logger = api_logger.get()


# NodePingInfo class to store the information of a active node
# TODO: SOme of the state info needs to be persisted in DB
class NodePingInfo(BaseModel):
    websocket: WebSocket
    node_uuid: UUID  # the UUID of the node, need this to update the metrics
    rtt: float = 0  # the last rtt of the node
    next_ping_time: float = 0  # the scheduled time to send the bext ping to the node
    ping_streak: int = 0  # no of consecutive pings that the node has responded to
    miss_streak: int = 0  # no of consecutive pings that the node has missed
    waiting_for_pong: bool = False  # flag to check if the node is waiting for pong
    ping_nonce: str = (
        ""  # the nonce of the last ping sent to the node to avoid replay attacks
    )
    ping_sent_time: float = 0  # the time when the last ping was sent to the node

    model_config = ConfigDict(arbitrary_types_allowed=True)


class PingPongProtocol:
    def __init__(self, metrics_queue_repository: MetricsQueueRepository):
        self.metrics_queue_repository = metrics_queue_repository
        self.active_nodes = {}
        logger.info(f"{settings.PING_PONG_PROTOCOL_NAME}: Protocol initialized")

    # Handle the responses from the client
    async def handle(self, data: Any):
        # record the time ASAP so that we exclude processing time of the pong.
        pong_received_time = _current_milli_time()
        # TODO: we should replace these mess with direct pydantic model objects once the
        # inference is inside the protocol. Until then, we will use the dict objects and manually
        # validate them.
        pong_response = _extract_and_validate(data)
        if pong_response is None:
            logger.warning(
                f"{settings.PING_PONG_PROTOCOL_NAME}: Invalid data received: {data}"
            )
            return

        if pong_response.node_id not in self.active_nodes:
            logger.warning(
                f"{settings.PING_PONG_PROTOCOL_NAME}: Received pong from an unknown node {pong_response.node_id}"
            )
            return

        node_info = self.active_nodes[pong_response.node_id]
        if _pong_protocol_validations(node_info, pong_response) is False:
            return

        await self.got_pong_on_time(
            pong_response.node_id, node_info, pong_received_time
        )

    # Regularly check if we have received the pong responses and to send ping messages
    async def job(self):
        await self.send_pings()
        await self.check_for_pongs()

    # Add a node to the active nodes dictionary
    # called when a new node connects to the server through websocket
    def add_node(self, node_uuid: UUID, node_id: str, websocket: WebSocket) -> bool:
        if node_id in self.active_nodes:
            logger.warning(
                f"{settings.PING_PONG_PROTOCOL_NAME}: Node {node_id} already exists in the active nodes"
            )
            return False
        current_time = _current_milli_time()
        self.active_nodes[node_id] = NodePingInfo(
            websocket=websocket,
            node_uuid=node_uuid,
            rtt=0,
            next_ping_time=current_time + (settings.PING_INTERVAL_IN_SECONDS * 1000),
            ping_streak=0,
            miss_streak=0,
            waiting_for_pong=False,
            ping_nonce="",
            ping_sent_time=current_time,
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
                if round(_current_milli_time() - node_info.ping_sent_time) > (
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
        node_info.ping_sent_time = _current_milli_time()  # update the last ping time
        node_info.ping_nonce = str(uuid.uuid4())  # g

        # Construct the ping request
        ping_request = PingRequest(
            protocol_version=settings.PING_PONG_PROTOCOL_VERSION,
            message_type=PingPongMessageType.PING,
            node_id=node_id,  # the node id of the client
            nonce=node_info.ping_nonce,  # the nonce of the ping request
            rtt=node_info.rtt,  # send the previously observed RTT to client
            ping_streak=node_info.ping_streak,  # send the ping streak to client
            miss_streak=node_info.miss_streak,  # send the miss streak to client
        )

        # Send the ping to the client
        websocket = self.active_nodes[node_id].websocket
        message = {
            "protocol": settings.PING_PONG_PROTOCOL_NAME,
            "data": jsonable_encoder(ping_request),
        }
        await websocket.send_json(message)
        logger.info(
            f"{settings.PING_PONG_PROTOCOL_NAME}: Sent ping to node {node_id}, with nonce {node_info.ping_nonce}"
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
                f"{settings.PING_PONG_PROTOCOL_NAME}: Missed pong from node {node_id}, with nonce {node_info.ping_nonce}"
            )

    async def got_pong_on_time(self, node_id, node_info, pong_received_time):
        # Update the state of the client
        node_info.next_ping_time = _current_milli_time() + (
            settings.PING_INTERVAL_IN_SECONDS * 1000
        )  # set the next ping time
        node_info.waiting_for_pong = False  # reset the waiting for pong flag
        node_info.miss_streak = 0  # resset miss streak if any
        node_info.ping_streak += 1  # increment the ping streak
        node_info.rtt = (
            pong_received_time - node_info.ping_sent_time
        )  # calculate the rtt
        node_info.ping_sent_time = 0  # reset the ping sent time
        await _update_rtt(
            node_info.node_uuid, node_info.rtt, self.metrics_queue_repository
        )
        logger.info(
            f"{settings.PING_PONG_PROTOCOL_NAME}: Received pong from node {node_id}, with nonce {node_info.ping_nonce} with rtt {node_info.rtt} in msec"
        )


def _current_milli_time():
    return round(time.time() * 1000)


def _extract_and_validate(data: Any) -> PongResponse | None:
    try:
        message_type = PingPongMessageType(data.get("message_type"))
    except KeyError:
        return None

    pong_response = PongResponse(
        protocol_version=data.get("protocol_version"),
        message_type=message_type,
        node_id=data.get("node_id"),
        nonce=data.get("nonce"),
    )
    if (
        pong_response.protocol_version is None
        or pong_response.node_id is None
        or pong_response.nonce is None
    ):
        return None
    return pong_response


def _pong_protocol_validations(
    node_info: NodePingInfo, pong_response: PongResponse
) -> bool:
    # check if we received the correct protocol version
    if pong_response.protocol_version != settings.PING_PONG_PROTOCOL_VERSION:
        logger.warning(
            f"{settings.PING_PONG_PROTOCOL_NAME}: Received pong with invalid protocol version from node {pong_response.node_id}"
        )
        return False

    # check if we received PONG message
    if PingPongMessageType(pong_response.message_type) != PingPongMessageType.PONG:
        logger.warning(
            f"{settings.PING_PONG_PROTOCOL_NAME}: Received unexpected message type from node {pong_response.node_id}, {pong_response.message_type}"
        )
        return False

    if not node_info.waiting_for_pong:
        logger.warning(
            f"{settings.PING_PONG_PROTOCOL_NAME}: Received unexpected pong from node {pong_response.node_id}"
        )
        return False

    if (
        pong_response.nonce != node_info.ping_nonce
    ):  # check the nonce matches the one sent in Ping
        logger.warning(
            f"{settings.PING_PONG_PROTOCOL_NAME}: Received pong with invalid nonce from node {pong_response.node_id}, expected {node_info.ping_nonce}, got {pong_response.nonce}"
        )
        return False

    return True


async def _update_rtt(
    node_uuid: UUID,
    rtt: int,
    metrics_queue_repository: MetricsQueueRepository,
) -> None:
    node_metrics_increment = NodeMetricsIncrement(node_id=node_uuid)
    node_metrics_increment.rtt = rtt  # dont increment, just update the rtt
    await metrics_queue_repository.push(node_metrics_increment)
