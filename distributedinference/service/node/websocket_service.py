import json
import time
from typing import Optional

from fastapi import WebSocket
from fastapi import WebSocketDisconnect
from fastapi.exceptions import WebSocketRequestValidationError

import settings
from distributedinference import api_logger
from distributedinference.domain.node.entities import ConnectedNode
from distributedinference.domain.node.entities import NodeMetrics
from distributedinference.domain.user.entities import User
from distributedinference.repository.node_repository import NodeRepository

logger = api_logger.get()


async def execute(
    websocket: WebSocket,
    user: User,
    model_name: Optional[str],
    node_repository: NodeRepository,
):
    logger.info(f"Node, with user id {user.uid}, trying to connect")
    await websocket.accept()

    if not model_name:
        raise WebSocketRequestValidationError('No "Model" header provided')
    benchmark = await node_repository.get_node_benchmark(user.uid, model_name)
    if not benchmark:
        raise WebSocketRequestValidationError("Benchmarking is not completed")
    if benchmark.tokens_per_second < settings.MINIMUM_COMPLETIONS_TOKENS_PER_SECOND:
        raise WebSocketRequestValidationError("Benchmarking performance is too low")

    node_id = user.uid
    node_metrics = await node_repository.get_node_metrics(node_id) or NodeMetrics()
    node = ConnectedNode(
        uid=node_id,
        model=model_name,
        connected_at=int(time.time()),
        websocket=websocket,
        request_incoming_queues={},
        metrics=node_metrics,
    )
    logger.info(f"Node {node_id} connected")
    connect_time = time.time()
    if not node_repository.register_node(node):
        raise WebSocketRequestValidationError(
            "Node with same API key already connected"
        )
    try:
        while True:
            data = await websocket.receive_text()
            request_id = None
            try:
                parsed_data = json.loads(data)
                # get request id
                request_id = parsed_data["request_id"]
            except json.JSONDecodeError:
                raise WebSocketRequestValidationError("Invalid JSON data")
            try:
                await node.request_incoming_queues[request_id].put(parsed_data)
            except KeyError:
                logger.error(f"Received chunk for unknown request {request_id}")
    except WebSocketDisconnect:
        node_repository.deregister_node(node_id)
        uptime = int(time.time() - connect_time)
        async with node.metrics.lock:
            node.metrics.uptime += uptime
        await node_repository.save_node_metrics(node_id, node.metrics)
        logger.info(f"Node {node_id} disconnected")
