import asyncio
import random
from dataclasses import asdict
from typing import Dict
from typing import List
from typing import Optional
from uuid import UUID

from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from openai.types.chat import ChatCompletionChunk

from distributedinference import api_logger
from distributedinference.domain.node.entities import ConnectedNode
from distributedinference.domain.node.entities import ImageGenerationWebsocketRequest
from distributedinference.domain.node.entities import ImageGenerationWebsocketResponse
from distributedinference.domain.node.entities import InferenceError
from distributedinference.domain.node.entities import InferenceErrorStatusCodes
from distributedinference.domain.node.entities import InferenceRequest
from distributedinference.domain.node.entities import InferenceResponse
from distributedinference.domain.node.entities import InferenceStatusCodes
from distributedinference.domain.node.entities import NodeStatus

logger = api_logger.get()


class ConnectedNodeRepository:
    _max_parallel_requests_per_node: int
    _max_parallel_requests_per_datacenter_node: int

    # node_id: ConnectedNode
    _connected_nodes: Dict[UUID, ConnectedNode]

    def __init__(
        self,
        max_parallel_requests_per_node: int,
        max_parallel_requests_per_datacenter_node: int,
    ):
        self._max_parallel_requests_per_node = max_parallel_requests_per_node
        self._max_parallel_requests_per_datacenter_node = (
            max_parallel_requests_per_datacenter_node
        )
        self._connected_nodes = {}

    def register_node(self, connected_node: ConnectedNode) -> bool:
        """
        Register a connected node, returns True if the node was successfully registered, False if the node is already registered
        """
        if connected_node.uid not in self._connected_nodes:
            self._connected_nodes[connected_node.uid] = connected_node
            return True
        return False

    def deregister_node(self, node_id: UUID):
        if node_id in self._connected_nodes:
            # Send error to all active requests
            for request_id, queue in self._connected_nodes[
                node_id
            ].request_incoming_queues.items():
                queue.put_nowait(
                    InferenceResponse(
                        node_id=node_id,
                        request_id=request_id,
                        error=InferenceError(
                            status_code=InferenceErrorStatusCodes.UNPROCESSABLE_ENTITY,
                            message="Node disconnected",
                        ),
                    ).to_dict()
                )
            del self._connected_nodes[node_id]

    def select_node(self, model: str) -> Optional[ConnectedNode]:
        if not self._connected_nodes:
            return None

        eligible_nodes = [
            node
            for node in self._connected_nodes.values()
            if node.model == model and self._can_handle_new_request(node)
        ]

        if not eligible_nodes:
            return None

        return random.choice(eligible_nodes)

    def _can_handle_new_request(self, node: ConnectedNode) -> bool:
        if not node.is_self_hosted and not node.node_status.is_healthy():
            return False
        if node.is_datacenter_gpu():
            return (
                node.active_requests_count()
                < self._max_parallel_requests_per_datacenter_node
            )
        if node.can_handle_parallel_requests():
            return node.active_requests_count() < self._max_parallel_requests_per_node

        return node.active_requests_count() == 1

    async def close_node_connection(self, node_id: UUID):
        if node_id in self._connected_nodes:
            await self._connected_nodes[node_id].websocket.close(
                code=http_status.WS_1008_POLICY_VIOLATION,
                reason="No Inference result",
            )

    def get_locally_connected_nodes(self) -> List[ConnectedNode]:
        return list(self._connected_nodes.values())

    def get_locally_connected_node_keys(self) -> List[UUID]:
        return list(self._connected_nodes.keys())

    async def send_inference_request(
        self, node_id: UUID, request: InferenceRequest
    ) -> bool:
        if node_id in self._connected_nodes:
            connected_node = self._connected_nodes[node_id]
            connected_node.request_incoming_queues[request.id] = asyncio.Queue()
            await connected_node.websocket.send_json(asdict(request))
            return True
        return False

    async def send_image_generation_request(
        self, node_id: UUID, request: ImageGenerationWebsocketRequest
    ) -> bool:
        if node_id in self._connected_nodes:
            connected_node = self._connected_nodes[node_id]
            connected_node.request_incoming_queues[request.request_id] = asyncio.Queue()
            await connected_node.websocket.send_json(jsonable_encoder(request))
            return True
        return False

    async def receive_for_request(
        self, node_id: UUID, request_id: str
    ) -> Optional[InferenceResponse]:
        if node_id in self._connected_nodes:
            connected_node = self._connected_nodes[node_id]
            data = await connected_node.request_incoming_queues[request_id].get()
            try:
                return InferenceResponse(
                    node_id=node_id,
                    request_id=data["request_id"],
                    chunk=(
                        ChatCompletionChunk(**data["chunk"])
                        if data.get("chunk")
                        else None
                    ),
                    error=(
                        InferenceError(**data["error"]) if data.get("error") else None
                    ),
                    status=(
                        InferenceStatusCodes(data["status"])
                        if data.get("status")
                        else None
                    ),
                )
            except Exception:
                logger.warning(f"Failed to parse chunk, request_id={request_id}")
                return None
        return None

    async def receive_for_image_generation_request(
        self, node_id: UUID, request_id: str
    ) -> Optional[ImageGenerationWebsocketResponse]:
        if node_id in self._connected_nodes:
            connected_node = self._connected_nodes[node_id]
            data = await connected_node.request_incoming_queues[request_id].get()
            try:
                return ImageGenerationWebsocketResponse(
                    node_id=node_id,
                    request_id=data["request_id"],
                    images=data["images"],
                    error=data["error"],
                )
            except Exception:
                logger.warning(
                    f"Failed to parse image generation response, request_id={request_id}"
                )
                logger.debug(f"Received data: {data}")
                return None
        return None

    def cleanup_request(self, node_id: UUID, request_id: str) -> None:
        if node_id in self._connected_nodes:
            connected_node = self._connected_nodes[node_id]
            del connected_node.request_incoming_queues[request_id]

    def update_node_status(self, node_id: UUID, status: NodeStatus) -> bool:
        if node_id in self._connected_nodes:
            self._connected_nodes[node_id].node_status = status
            return True
        return False
