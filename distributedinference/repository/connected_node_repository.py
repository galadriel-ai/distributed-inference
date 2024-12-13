import asyncio
from dataclasses import asdict
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from uuid import UUID

from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from openai.types.chat import ChatCompletionChunk

from distributedinference import api_logger
from distributedinference.domain.node.entities import ConnectedNode, BackendHost
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
    _backend_host: Optional[BackendHost]

    def __init__(
        self,
        max_parallel_requests_per_node: int,
        max_parallel_requests_per_datacenter_node: int,
        hostname: str,
    ):
        self._max_parallel_requests_per_node = max_parallel_requests_per_node
        self._max_parallel_requests_per_datacenter_node = (
            max_parallel_requests_per_datacenter_node
        )
        self._connected_nodes = {}
        try:
            self._backend_host = BackendHost.from_value(hostname)
        except TypeError as e:
            logger.error(f"Failed to initialize BackendHost: {e}")
            self._backend_host = None

    def register_node(self, connected_node: ConnectedNode) -> bool:
        """
        Register a connected node, returns True if the node was successfully registered,
        False if the node is already registered
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

    def get_nodes_by_model(self, model: str) -> List[ConnectedNode]:
        return [node for node in self._connected_nodes.values() if node.model == model]

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

    async def send_json_request(self, node_id: UUID, request: Dict) -> bool:
        if node_id in self._connected_nodes:
            connected_node = self._connected_nodes[node_id]
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

    async def add_inference_response_chunk(
        self, node_id: UUID, request_id: str, parsed_data: Any
    ) -> None:
        if node_id in self._connected_nodes:
            connected_node = self._connected_nodes[node_id]
            try:
                await connected_node.request_incoming_queues[request_id].put(
                    parsed_data
                )
            except KeyError:
                logger.error(
                    f"Received chunk for unknown request {request_id}, chunk: {parsed_data}"
                )

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
            finally:
                # Remove the request from the queue
                del connected_node.request_incoming_queues[request_id]
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

    def get_backend_host(self) -> Optional[BackendHost]:
        return self._backend_host
