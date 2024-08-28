from typing import AsyncGenerator

from distributedinference.domain.node.entities import InferenceRequest
from distributedinference.domain.node.entities import InferenceResponse
from distributedinference.repository.node_repository import NodeRepository


async def execute(
    request: InferenceRequest, node_repository: NodeRepository
) -> AsyncGenerator[InferenceResponse, None]:
    node_id = node_repository.select_node(request.model)
    await node_repository.send_inference_request(node_id, request)
    try:
        while True:
            response = await node_repository.receive_for_request(node_id, request.id)
            if response is None or response.chunk.choices[0].finish_reason == "stop":
                break
            yield response
    finally:
        await node_repository.cleanup_request(node_id, request.id)
