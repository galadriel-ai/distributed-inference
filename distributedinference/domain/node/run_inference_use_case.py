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
    is_stream = bool(request.chat_request.get("stream"))
    is_include_usage: bool = bool(
        (request.chat_request.get("stream_options") or {}).get("include_usage")
    )
    try:
        while True:
            response = await node_repository.receive_for_request(node_id, request.id)
            yield response
            if is_stream and is_include_usage:
                # If is_stream and is_include_usage last chunk has no choices, only usage info
                if not len(response.chunk.choices):
                    break
            else:
                if response.chunk.choices[0].finish_reason == "stop":
                    break
            if response.error:
                break
    finally:
        await node_repository.cleanup_request(node_id, request.id)
