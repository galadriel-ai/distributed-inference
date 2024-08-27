import asyncio
import json

from fastapi import APIRouter
from fastapi import Depends
from fastapi import WebSocket
from fastapi import WebSocketDisconnect
from fastapi.exceptions import WebSocketRequestValidationError

from distributedinference import api_logger
from distributedinference import dependencies
from distributedinference.domain.node.entities import ConnectedNode
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.user_repository import UserRepository
from distributedinference.service.auth import authentication

TAG = "Node"
router = APIRouter(prefix="/node")
router.tags = [TAG]

logger = api_logger.get()


@router.websocket(
    "/ws",
    name="Node WebSocket",
)
async def websocket_endpoint(
    websocket: WebSocket,
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    user_repository: UserRepository = Depends(dependencies.get_user_repository),
):
    user = await authentication.validate_api_key(
        websocket.headers.get("Authorization"),
        user_repository,
    )
    if not user:
        raise WebSocketRequestValidationError("Authorization header is required")

    logger.info(f"Node, with user id {user.uid}, trying to connect")
    await websocket.accept()
    node_id = user.uid
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
