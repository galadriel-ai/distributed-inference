from typing import AsyncGenerator

from distributedinference.repository.node_repository import NodeRepository
from distributedinference.domain.node.entities import InferenceRequest
from distributedinference.domain.node.entities import InferenceResponse


async def execute(
    request: InferenceRequest, node_repository: NodeRepository
) -> AsyncGenerator[InferenceResponse, None]:
    node_id = node_repository.select_node(request.model)
    await node_repository.send_inference_request(node_id, request)
    while True:
        response = await node_repository.receive(node_id)
        if response is None or response.finish_reason == "stop":
            break
        yield response
