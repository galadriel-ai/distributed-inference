import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.exceptions import WebSocketRequestValidationError

from distributedinference import api_logger
from distributedinference.domain.node.entities import ConnectedNode
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.dependencies import get_node_repository

TAG = "Node"
router = APIRouter(prefix="/node")
router.tags = [TAG]

logger = api_logger.get()


@router.websocket(
    "/ws",
    name="Node WebSocket",
)
async def websocket_endpoint(
    websocket: WebSocket, node_repository: NodeRepository = Depends(get_node_repository)
):
    node_id = websocket.headers.get("Authorization")
    logger.info(f"Node {node_id} trying to connect")
    if not node_id:
        raise WebSocketRequestValidationError("Authorization header is required")

    logger.info(f"Node {node_id} trying to connect")
    await websocket.accept()
    node = ConnectedNode(
        uid=node_id, model="model", websocket=websocket, message_queue=asyncio.Queue()
    )
    logger.info(f"Node {node_id} connected")
    node_repository.register_node(node)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                parsed_data = json.loads(data)
            except json.JSONDecodeError:
                raise WebSocketRequestValidationError("Invalid JSON data")
            await node.message_queue.put(parsed_data)
    except WebSocketDisconnect:
        node_repository.deregister_node(node_id)
        logger.info(f"Node {node_id} disconnected")
