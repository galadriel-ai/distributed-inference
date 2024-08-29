from typing import AsyncGenerator

from distributedinference.domain.node.exceptions import NoAvailableNodesError
from distributedinference.domain.node.entities import InferenceRequest
from distributedinference.domain.node.entities import InferenceResponse
from distributedinference.repository.node_repository import NodeRepository


async def execute(
    request: InferenceRequest, node_repository: NodeRepository
) -> AsyncGenerator[InferenceResponse, None]:
    node_id = node_repository.select_node(request.model)
    if not node_id:
        raise NoAvailableNodesError()
    await node_repository.send_inference_request(node_id, request)
    try:
        while True:
            response = await node_repository.receive_for_request(node_id, request.id)
            yield response
            if response.chunk.choices[0].finish_reason == "stop":
                break
            if response.error:
                break
    finally:
        await node_repository.cleanup_request(node_id, request.id)
