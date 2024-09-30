import json
import time

from fastapi import WebSocket
from fastapi import WebSocketDisconnect
from fastapi.exceptions import WebSocketRequestValidationError

from distributedinference import api_logger
from distributedinference.domain.user.entities import User
from distributedinference.domain.node.entities import ConnectedNode
from distributedinference.domain.node.entities import NodeMetrics
from distributedinference.repository.node_repository import NodeRepository

logger = api_logger.get()


async def execute(
    websocket: WebSocket,
    user: User,
    node_repository: NodeRepository,
):
    logger.info(f"Node, with user id {user.uid}, trying to connect")
    await websocket.accept()
    node_id = user.uid
    node_metrics = await node_repository.get_node_metrics(node_id) or NodeMetrics()
    print(await node_metrics.get_uptime())
    node = ConnectedNode(
        uid=node_id,
        model="model",
        websocket=websocket,
        request_incoming_queues={},
        metrics=node_metrics,
    )
    logger.info(f"Node {node_id} connected")
    connect_time = time.time()
    if not node_repository.register_node(node):
        raise WebSocketRequestValidationError("Node already connected")
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
        print("Node metrics", await node.metrics.get_uptime())
        await node.metrics.add_uptime(uptime)
        print("Node metrics", await node.metrics.get_uptime())
        await node_repository.save_node_metrics(node_id, node.metrics)
        logger.info(f"Node {node_id} disconnected")
