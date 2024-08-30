import json

from fastapi import APIRouter
from fastapi import Depends
from fastapi import WebSocket
from fastapi import WebSocketDisconnect
from fastapi.exceptions import WebSocketRequestValidationError

from distributedinference import api_logger
from distributedinference import dependencies
from distributedinference.domain.node.entities import ConnectedNode
from distributedinference.domain.node.entities import NodeMetrics
from distributedinference.domain.user.entities import User
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.user_repository import UserRepository
from distributedinference.service.auth import authentication
from distributedinference.service.node import get_node_info_service
from distributedinference.service.node import save_node_info_service
from distributedinference.service.node.entities import GetNodeInfoResponse
from distributedinference.service.node.entities import PostNodeInfoRequest
from distributedinference.service.node.entities import PostNodeInfoResponse

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
        uid=node_id,
        model="model",
        websocket=websocket,
        request_incoming_queues={},
        metrics=NodeMetrics(),
    )
    logger.info(f"Node {node_id} connected")
    node_repository.register_node(node)
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
        logger.info(f"Node {node_id} disconnected")


@router.get(
    "/info",
    name="Node Info",
    response_model=GetNodeInfoResponse,
)
async def node_info(
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    user: User = Depends(authentication.validate_api_key_header),
):
    return await get_node_info_service.execute(user, node_repository)


@router.post(
    "/info",
    name="Node Info",
    response_model=PostNodeInfoResponse,
)
async def node_info(
    request: PostNodeInfoRequest,
    node_repository: NodeRepository = Depends(dependencies.get_node_repository),
    user: User = Depends(authentication.validate_api_key_header),
):
    return await save_node_info_service.execute(request, user.uid, node_repository)
