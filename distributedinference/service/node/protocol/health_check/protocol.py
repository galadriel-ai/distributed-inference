import time
import uuid
from dataclasses import dataclass
from typing import Any
from typing import Dict
from typing import Optional
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from packaging import version

import settings
from distributedinference.api_logger import api_logger
from distributedinference.domain.node.entities import NodeGPUHealth
from distributedinference.domain.node.entities import NodeHealth
from distributedinference.repository.connected_node_repository import (
    ConnectedNodeRepository,
)
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.node.protocol.health_check.entities import (
    HealthCheckMessageType,
)
from distributedinference.service.node.protocol.health_check.entities import (
    HealthCheckRequest,
)
from distributedinference.service.node.protocol.health_check.entities import (
    HealthCheckResponse,
)

logger = api_logger.get()

SUPPORTED_NODE_VERSION = "0.0.15"


@dataclass
class NodeHealthCheckInfo:
    node_uuid: UUID

    next_request_time: float = 0
    waiting_for_response: bool = False
    last_request_nonce: Optional[str] = None


class HealthCheckProtocol:
    PROTOCOL_NAME = "health-check"
    PROTOCOL_VERSION = "1.0"

    def __init__(
        self,
        node_repository: NodeRepository,
        connected_node_repository: ConnectedNodeRepository,
    ):
        self.node_repository = node_repository
        self.connected_node_repository = connected_node_repository
        self.active_nodes: Dict[str, NodeHealthCheckInfo] = {}
        logger.info(f"{self.PROTOCOL_NAME}: Protocol initialized")

    async def handle(self, data: Any) -> Any:
        try:
            response = HealthCheckResponse(**data)
        except:
            logger.warning(f"{self.PROTOCOL_NAME}: Invalid data received: {data}")
            return None

        if response.node_id not in self.active_nodes:
            logger.warning(
                f"{self.PROTOCOL_NAME}: Received health check response from an unknown node {response.node_id}"
            )
            return None

        node_info = self.active_nodes[response.node_id]
        if (
            _protocol_validations(
                node_info,
                response,
                self.PROTOCOL_NAME,
                self.PROTOCOL_VERSION,
            )
            is False
        ):
            return None

        await self._received_health_check_response(response, node_info)

    async def run(self):
        await self._send_health_check_requests()

    def add_node(
        self,
        node_uuid: UUID,
        node_id: str,
        node_version: Optional[str],
    ) -> bool:
        if node_id in self.active_nodes:
            logger.warning(
                f"{self.PROTOCOL_NAME}: Node {node_id} already exists in the active nodes"
            )
            return False
        if not _is_supported_node_version(node_version):
            logger.warning(
                f"{self.PROTOCOL_NAME}: Node {node_id} is using an unsupported version {node_version}"
            )
            return False
        self.active_nodes[node_id] = NodeHealthCheckInfo(
            node_uuid=node_uuid,
            next_request_time=_current_milli_time()
            + settings.NODE_HEALTH_CHECK_INTERVAL_SECONDS * 1000,
            last_request_nonce=None,
        )
        logger.info(
            f"{self.PROTOCOL_NAME}: Node {node_id} has been added to the active nodes"
        )
        return True

    async def remove_node(self, node_id: str) -> bool:
        if node_id not in self.active_nodes:
            logger.warning(
                f"{self.PROTOCOL_NAME}: Node {node_id} does not exist in the active nodes"
            )
            return False
        del self.active_nodes[node_id]
        logger.info(
            f"{self.PROTOCOL_NAME}: Node {node_id} has been deleted from the active nodes"
        )
        return True

    async def remove_node_by_uid(self, node_uid: UUID) -> bool:
        for node_id, node in self.active_nodes.items():
            if node.node_uuid == node_uid:
                return await self.remove_node(node_id)
        return False

    async def _send_health_check_requests(self):
        current_time = _current_milli_time()
        for node_id, node_info in self.active_nodes.items():
            if current_time > node_info.next_request_time:
                if not node_info.waiting_for_response:
                    await self._send_health_check_request(node_id)

    async def _send_health_check_request(self, node_id: str):
        node_info = self.active_nodes[node_id]
        nonce = str(uuid.uuid4())
        health_check_request = HealthCheckRequest(
            protocol_version=self.PROTOCOL_VERSION,
            message_type=HealthCheckMessageType.HEALTH_CHECK_REQUEST,
            node_id=node_id,
            nonce=nonce,
        )

        message = {
            "protocol": self.PROTOCOL_NAME,
            "data": jsonable_encoder(health_check_request),
        }
        if await self.connected_node_repository.send_json_request(
            node_info.node_uuid, message
        ):
            node_info.next_request_time = 0
            node_info.waiting_for_response = True
            node_info.last_request_nonce = nonce
            logger.info(
                f"{self.PROTOCOL_NAME}: Sent health check request to node {node_id}, sent time = {_current_milli_time()}, nonce = {nonce}"
            )
        else:
            logger.error(
                f"{self.PROTOCOL_NAME}: Failed to send health check request to node {node_id}"
            )

    async def _received_health_check_response(
        self, response: HealthCheckResponse, node_info: NodeHealthCheckInfo
    ):
        node_info.next_request_time = _current_milli_time() + (
            settings.NODE_HEALTH_CHECK_INTERVAL_SECONDS * 1000
        )
        node_info.waiting_for_response = False
        node_info.last_request_nonce = None

        node_health = NodeHealth(
            node_id=node_info.node_uuid,
            cpu_percent=response.cpu_percent,
            ram_percent=response.ram_percent,
            disk_percent=response.disk_percent,
            gpus=[
                NodeGPUHealth(
                    gpu_percent=gpu.gpu_percent,
                    vram_percent=gpu.vram_percent,
                    power_percent=gpu.power_percent,
                )
                for gpu in response.gpus
            ],
        )
        await self.node_repository.save_node_health(
            node_id=node_info.node_uuid,
            health=node_health,
        )
        logger.info(
            f"{self.PROTOCOL_NAME}: Received health check response from node {response.node_id}, nonce = {response.nonce}"
        )


def _current_milli_time():
    return time.time_ns() // 1_000_000


def _is_supported_node_version(node_version: Optional[str]) -> bool:
    if not node_version:
        return False
    return version.parse(node_version) >= version.parse(SUPPORTED_NODE_VERSION)


def _protocol_validations(
    node_info: NodeHealthCheckInfo,
    response: HealthCheckResponse,
    protocol_name: str,
    protocol_version: str,
) -> bool:
    if response.protocol_version != protocol_version:
        logger.warning(
            f"{protocol_name}: Received pong with invalid protocol version from node {response.node_id}"
        )
        return False
    if (
        HealthCheckMessageType(response.message_type)
        != HealthCheckMessageType.HEALTH_CHECK_RESPONSE
    ):
        logger.warning(
            f"{protocol_name}: Received unexpected message type from node {response.node_id}, {response.message_type}"
        )
        return False

    if not node_info.waiting_for_response:
        logger.warning(
            f"{protocol_name}: Received unexpected health check response from node {response.node_id}"
        )
        return False

    if response.nonce != node_info.last_request_nonce:
        logger.warning(
            f"{protocol_name}: Received health check response with invalid nonce from node {response.node_id}, expected {node_info.last_request_nonce}, got {response.nonce}"
        )
        return False
    return True
