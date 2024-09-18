import json
import time
from typing import Optional
from uuid import UUID

from fastapi import WebSocket
from fastapi import WebSocketDisconnect
from fastapi.exceptions import WebSocketRequestValidationError

import settings
from distributedinference import api_logger
from distributedinference.analytics.analytics import (
    Analytics,
    AnalyticsEvent,
    EventName,
)
from distributedinference.domain.node.entities import ConnectedNode
from distributedinference.domain.node.entities import NodeInfo
from distributedinference.domain.node.entities import NodeMetricsIncrement
from distributedinference.domain.user.entities import User
from distributedinference.repository.metrics_queue_repository import (
    MetricsQueueRepository,
)
from distributedinference.repository.node_repository import NodeRepository

logger = api_logger.get()


# pylint: disable=R0913, R0914
async def execute(
    websocket: WebSocket,
    user: User,
    node_info: NodeInfo,
    model_name: Optional[str],
    node_repository: NodeRepository,
    metrics_queue_repository: MetricsQueueRepository,
    analytics: Analytics,
):
    logger.info(
        f"Node with user id {user.uid} and node id {node_info.node_id}, trying to connect"
    )
    await websocket.accept()

    if not model_name:
        raise WebSocketRequestValidationError('No "Model" header provided')
    benchmark = await node_repository.get_node_benchmark(
        user.uid, node_info.node_id, model_name
    )
    if not benchmark:
        raise WebSocketRequestValidationError("Benchmarking is not completed")
    if benchmark.tokens_per_second < settings.MINIMUM_COMPLETIONS_TOKENS_PER_SECOND:
        raise WebSocketRequestValidationError("Benchmarking performance is too low")

    node_uid = node_info.node_id
    node = ConnectedNode(
        uid=node_uid,
        model=model_name,
        vram=node_info.vram,
        connected_at=int(time.time()),
        websocket=websocket,
        request_incoming_queues={},
    )
    logger.info(f"Node {node_uid} connected")
    analytics.track_event(user.uid, AnalyticsEvent(EventName.WS_NODE_CONNECTED, {}))

    connect_time = time.time()
    if not node_repository.register_node(node):
        raise WebSocketRequestValidationError(
            "Node with same node id already connected"
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
    except WebSocketRequestValidationError as e:
        node_repository.deregister_node(node_uid)
        uptime = int(time.time() - connect_time)
        await _increment_uptime(node.uid, uptime, metrics_queue_repository)
        logger.info(f"Node {node_uid} disconnected, because of invalid JSON")
        analytics.track_event(
            user.uid, AnalyticsEvent(EventName.WS_NODE_DISCONNECTED_WITH_ERROR, {})
        )
        raise e
    except WebSocketDisconnect:
        node_repository.deregister_node(node_uid)
        uptime = int(time.time() - connect_time)
        await _increment_uptime(node.uid, uptime, metrics_queue_repository)
        logger.info(f"Node {node_uid} disconnected")
        analytics.track_event(
            user.uid, AnalyticsEvent(EventName.WS_NODE_DISCONNECTED, {})
        )


async def _increment_uptime(
    node_id: UUID,
    uptime: int,
    metrics_queue_repository: MetricsQueueRepository,
) -> None:
    node_metrics_increment = NodeMetricsIncrement(node_id=node_id)
    node_metrics_increment.uptime_increment += uptime
    await metrics_queue_repository.push(node_metrics_increment)
