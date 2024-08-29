import asyncio
import random
from dataclasses import asdict
from typing import Dict
from typing import Optional
from uuid import UUID

from openai.types.chat import ChatCompletionChunk

from distributedinference import api_logger
from distributedinference.domain.node.entities import ConnectedNode
from distributedinference.domain.node.entities import InferenceError
from distributedinference.domain.node.entities import InferenceRequest
from distributedinference.domain.node.entities import InferenceResponse

logger = api_logger.get()


class NodeRepository:

    def __init__(self):
        self._connected_nodes: Dict[UUID, ConnectedNode] = {}

    def register_node(self, connected_node: ConnectedNode):
        self._connected_nodes[connected_node.uid] = connected_node

    def deregister_node(self, node_id: UUID):
        if node_id in self._connected_nodes:
            del self._connected_nodes[node_id]

    def select_node(self, model: str) -> Optional[UUID]:
        if not len(self._connected_nodes):
            return None
        return random.choice(list(self._connected_nodes.keys()))

    def get_nodes_count(self) -> int:
        return len(self._connected_nodes)

    async def send_inference_request(
        self, node_id: UUID, request: InferenceRequest
    ) -> bool:
        if node_id in self._connected_nodes:
            connected_node = self._connected_nodes[node_id]
            connected_node.request_incoming_queues[request.id] = asyncio.Queue()
            await connected_node.websocket.send_json(asdict(request))
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
                    request_id=data["request_id"],
                    chunk=(
                        ChatCompletionChunk(**data["chunk"])
                        if "chunk" in data
                        else None
                    ),
                    error=(
                        InferenceError(**data["error"]) if data.get("error") else None
                    ),
                )
            except Exception as e:
                logger.warning(f"Failed to parse chunk, request_id={request_id}")
        return None

    async def cleanup_request(self, node_id: UUID, request_id: str):
        if node_id in self._connected_nodes:
            connected_node = self._connected_nodes[node_id]
            del connected_node.request_incoming_queues[request_id]
