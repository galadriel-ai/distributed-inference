import time
import uuid
from typing import Any
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict
from starlette.websockets import WebSocket

import settings
from distributedinference import api_logger
from distributedinference.repository.metrics_queue_repository import (
    MetricsQueueRepository,
)
from distributedinference.service.node.protocol.entities import (
    PingRequest,
    PingPongMessageType,
    PongResponse,
)

logger = api_logger.get()


class PingPongConfig:
    name: str
    version: str
    ping_interval_in_msec: int
    ping_timeout_in_msec: int
    ping_miss_threshold: int


# NodePingInfo class to store all the information of a active node
class NodePingInfo(BaseModel):
    websocket: WebSocket
    node_uuid: UUID  # the UUID of the node, need this to update the metrics
    # Counters
    rtt: float = 0  # the last rtt of the node
    sum_rtt: float = 0  # the sum of all the rtt requests, used to get average rtt
    ping_streak: int = 0  # no of consecutive pings that the node has responded to
    miss_streak: int = 0  # no of consecutive pings that the node has missed
    histogram: dict = {}  # Histogram of rtt values
    # State
    next_ping_time: float = 0  # the scheduled time to send the next ping to the node
    waiting_for_pong: bool = False  # flag to check if the node is waiting for pong
    ping_nonce: str = (
        ""  # the nonce of the last ping sent to the node to avoid replay attacks
    )
    ping_sent_time: float = 0  # the time when the last ping was sent to the node
    model_config = ConfigDict(arbitrary_types_allowed=True)


class PingPongProtocol:
    def __init__(
        self,
        metrics_queue_repository: MetricsQueueRepository,
        protocol_name: str,
        config: dict,
    ):

        if _validate_config(protocol_name, config) is False:
            raise ValueError(f"Invalid configuration for {protocol_name}")

        # Initialize the protocol with the configurations
        self.config = PingPongConfig()
        self.config.name = protocol_name
        self.config.version = config.get("version")
        self.config.ping_interval_in_msec = (
            config.get("ping_interval_in_seconds") * 1000
        )
        self.config.ping_timeout_in_msec = config.get("ping_timeout_in_seconds") * 1000
        self.config.ping_miss_threshold = config.get("ping_miss_threshold")

        self.metrics_queue_repository = metrics_queue_repository
        # The main data structure that stores the active nodes
        # and its states related to the ping-pong protocol
        self.active_nodes = {}
        logger.info(f"{self.config.name}: Protocol initialized")

    # Handle the responses from the client
    async def handle(self, data: Any):
        # record the time ASAP so that we exclude processing time of the pong.
        pong_received_time = _current_milli_time()
        # TODO: we should replace these mess with direct pydantic model objects once the
        # inference is inside the protocol. Until then, we will use the dict objects and manually
        # validate them.
        pong_response = _extract_and_validate(data)
        if pong_response is None:
            logger.warning(f"{self.config.name}: Invalid data received: {data}")
            return

        if pong_response.node_id not in self.active_nodes:
            logger.warning(
                f"{self.config.name}: Received pong from an unknown node {pong_response.node_id}"
            )
            return

        node_info = self.active_nodes[pong_response.node_id]
        if (
            _pong_protocol_validations(
                node_info, pong_response, self.config.name, self.config.version
            )
            is False
        ):
            return

        await self.got_pong_on_time(
            pong_response.node_id, node_info, pong_received_time
        )

    # Regularly check if we have received the pong responses and to send ping messages
    async def run(self):
        await self.send_pings()
        await self.check_for_pongs()

    # Add a node to the active nodes dictionary
    # called when a new node connects to the server through websocket
    def add_node(self, node_uuid: UUID, node_id: str, websocket: WebSocket) -> bool:
        if node_id in self.active_nodes:
            logger.warning(
                f"{self.config.name}: Node {node_id} already exists in the active nodes"
            )
            return False
        current_time = _current_milli_time()
        self.active_nodes[node_id] = NodePingInfo(
            websocket=websocket,
            node_uuid=node_uuid,
            rtt=0,
            sum_rtt=0,
            ping_streak=0,
            miss_streak=0,
            histogram={},
            next_ping_time=current_time + self.config.ping_interval_in_msec,
            waiting_for_pong=False,
            ping_nonce="",
            ping_sent_time=current_time,
        )
        logger.info(
            f"{self.config.name}: Node {node_id} has been added to the active nodes"
        )
        return True

    # Remove a node from the active nodes dictionary
    # called when a node disconnects the websocket from the server
    def remove_node(self, node_id: str) -> bool:
        if node_id not in self.active_nodes:
            logger.warning(
                f"{self.config.name}: Node {node_id} does not exist in the active nodes"
            )
            return False

        del self.active_nodes[node_id]
        logger.info(
            f"{self.config.name}: Node {node_id} has been deleted from the active nodes"
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
                    self.config.ping_timeout_in_msec
                ):
                    await self.missed_pong(
                        node_id, node_info
                    )  # timed out, mark it as missed pong

    # Send a ping message to the client
    async def send_ping_message(self, node_id: str):
        node_info = self.active_nodes[node_id]
        nonce = str(uuid.uuid4())
        # Construct the ping request
        ping_request = PingRequest(
            protocol_version=self.config.version,
            message_type=PingPongMessageType.PING,
            node_id=node_id,  # the node id of the client
            nonce=nonce,  # the nonce of the ping request
            # Strictly not required for Ping-Pong,
            # But can be used on the client side to do some priority analysis
            rtt=node_info.rtt,  # send the previously observed RTT to client
            ping_streak=node_info.ping_streak,  # send the ping streak to client
            miss_streak=node_info.miss_streak,  # send the miss streak to client
        )

        # Send the ping to the client
        websocket = self.active_nodes[node_id].websocket
        message = {
            "protocol": self.config.name,
            "data": jsonable_encoder(ping_request),
        }
        sent_time = _current_milli_time()
        await websocket.send_json(message)

        # Update the state and the counters after sending the ping
        node_info.next_ping_time = 0  # reset the next ping time
        node_info.waiting_for_pong = True  # set the node to waiting for pong
        node_info.ping_nonce = nonce  # the nonce that was sent in the ping
        node_info.ping_sent_time = sent_time  # update the last ping time

        logger.info(
            f"{self.config.name}: Sent ping to node {node_id}, sent time = {sent_time}, nonce = {nonce}"
        )

    async def missed_pong(self, node_id: str, node_info: NodePingInfo):
        # Update state
        node_info.waiting_for_pong = False  # reset the waiting for pong flag
        node_info.ping_nonce = ""  # reset the ping nonce
        node_info.ping_sent_time = 0  # reset the ping sent time
        node_info.next_ping_time = (
            _current_milli_time() + self.config.ping_interval_in_msec
        )  # set the next ping time

        # Update counters if the pog is missed
        node_info.ping_streak = 0  # reset the ping streak
        node_info.miss_streak += 1  # increment the miss streak

        # If the ping is not responded more than X times, the node should be assumed to be dead.
        if node_info.miss_streak > 3:
            self.remove_node(
                node_id
            )  # remove the node from the active nodes if it has missed 3 pongs consecutively
            logger.error(
                f"{self.config.name}: Node {node_id} has been removed due to too many missed pongs"
            )
        else:
            logger.error(
                f"{self.config.name}: Missed pong from node {node_id}, nonce = {node_info.ping_nonce}, miss_streak = {node_info.miss_streak}"
            )

    async def got_pong_on_time(self, node_id: str, node_info: NodePingInfo):
        # Update the state of the client
        current_rtt = pong_received_time - node_info.ping_sent_time
        node_info.sum_rtt = node_info.sum_rtt + current_rtt
        node_info.next_ping_time = _current_milli_time() + (
            self.config.ping_interval_in_msec
        )  # set the next ping time
        node_info.miss_streak = 0  # resset miss streak if any
        node_info.ping_streak += 1  # increment the ping streak
        node_info.rtt = current_rtt  # calculate the rtt

        hist_bin = int(node_info.rtt / 10)  # 1 bin for every 10 mSec
        bin_str = f"{hist_bin * 10 + 1}-{hist_bin * 10 + 10}"

        if bin_str in node_info.histogram:
            node_info.histogram[bin_str] = node_info.histogram[bin_str] + 1
        else:
            node_info.histogram[bin_str] = 1

        node_info.waiting_for_pong = False  # reset the waiting for pong flag
        node_info.ping_sent_time = 0  # reset the ping sent time

        logger.info(
            f"{self.config.name}: Received pong from node {node_id}, nonce = {node_info.ping_nonce}, rtt = {node_info.rtt} mSec, ping streak = {node_info.ping_streak}, miss streak = {node_info.miss_streak}, average rtt = {node_info.sum_rtt / node_info.ping_streak} mSec"
        )
        logger.debug(f"{self.config.name}: Node {node_id} histogram of RTTs")
        for bin_str, count in node_info.histogram.items():
            if count > 0:
                logger.debug(f"{self.config.name}: Range {bin_str} mSec -> {count}")


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
    node_info: NodePingInfo,
    pong_response: PongResponse,
    protocol_name: str,
    protocol_version: str,
) -> bool:
    # check if we received the correct protocol version
    if pong_response.protocol_version != protocol_version:
        logger.warning(
            f"{protocol_name}: Received pong with invalid protocol version from node {pong_response.node_id}"
        )
        return False

    # check if we received PONG message
    if PingPongMessageType(pong_response.message_type) != PingPongMessageType.PONG:
        logger.warning(
            f"{protocol_name}: Received unexpected message type from node {pong_response.node_id}, {pong_response.message_type}"
        )
        return False

    if not node_info.waiting_for_pong:
        logger.warning(
            f"{protocol_name}: Received unexpected pong from node {pong_response.node_id}"
        )
        return False

    if (
        pong_response.nonce != node_info.ping_nonce
    ):  # check the nonce matches the one sent in Ping
        logger.warning(
            f"{protocol_name}: Received pong with invalid nonce from node {pong_response.node_id}, expected {node_info.ping_nonce}, got {pong_response.nonce}"
        )
        return False

    return True


def _validate_config(protocol_name: str, config: dict):
    if protocol_name != settings.PING_PONG_PROTOCOL_NAME or config is None:
        return False
    if config.get("version") is None or config.get("version") == "":
        return False
    if (
        config.get("ping_interval_in_seconds") is None
        or config.get("ping_interval_in_seconds") <= 1
    ):
        return False
    if (
        config.get("ping_timeout_in_seconds") is None
        or config.get("ping_timeout_in_seconds") <= 1
    ):
        return False

    if (config.get("ping_miss_threshold") is None) or (
        config.get("ping_miss_threshold") <= 1
    ):
        return False
    return True
