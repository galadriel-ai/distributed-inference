from dataclasses import asdict
from typing import Dict
from typing import Optional

from distributedinference.domain.node.entities import ConnectedNode
from distributedinference.domain.node.entities import InferenceRequest
from distributedinference.domain.node.entities import InferenceResponse


class NodeRepository:

    def __init__(self):
        self._connected_nodes: Dict[str, ConnectedNode] = {}

    def register_node(self, connected_node: ConnectedNode):
        self._connected_nodes[connected_node.uid] = connected_node

    def deregister_node(self, node_id: str):
        if node_id in self._connected_nodes:
            del self._connected_nodes[node_id]

    def select_node(self, model: str) -> Optional[str]:
        return (
            list(self._connected_nodes.keys())[0]
            if len(self._connected_nodes) > 0
            else None
        )

    async def send_inference_request(
        self, node_id: str, request: InferenceRequest
    ) -> bool:
        if node_id in self._connected_nodes:
            connected_node = self._connected_nodes[node_id]
            await connected_node.websocket.send_json(asdict(request))
            return True
        return False

    async def receive(self, node_id: str) -> Optional[InferenceResponse]:
        if node_id in self._connected_nodes:
            connected_node = self._connected_nodes[node_id]
            data = await connected_node.message_queue.get()
            return InferenceResponse(**data)
        return None
