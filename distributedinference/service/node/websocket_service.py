import time
from typing import Optional
from uuid import UUID

import orjson
from fastapi import WebSocket
from fastapi import WebSocketDisconnect
from fastapi import status
from fastapi.exceptions import WebSocketException
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
from distributedinference.repository.benchmark_repository import BenchmarkRepository
from distributedinference.repository.metrics_queue_repository import (
    MetricsQueueRepository,
)
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.node.protocol.ping_pong_protocol import (
    PingPongProtocol,
)
from distributedinference.service.node.protocol.protocol_handler import ProtocolHandler

logger = api_logger.get()


# pylint: disable=R0913, R0914
async def execute(
    websocket: WebSocket,
    user: User,
    node_info: NodeInfo,
    model_name: Optional[str],
    node_repository: NodeRepository,
    benchmark_repository: BenchmarkRepository,
    metrics_queue_repository: MetricsQueueRepository,
    analytics: Analytics,
    protocol_handler: ProtocolHandler,
):
    logger.info(
        f"Node with user id {user.uid} and node id {node_info.node_id}, trying to connect"
    )
    await websocket.accept()

    await _check_before_connecting(model_name, node_info, benchmark_repository, user)

    node_uid = node_info.node_id
    node = ConnectedNode(
        uid=node_uid,
        user_id=user.uid,
        model=model_name,
        vram=node_info.vram,
        connected_at=int(time.time()),
        websocket=websocket,
        request_incoming_queues={},
    )
    logger.info(f"Node {node_uid} connected")
    analytics.track_event(
        user.uid,
        AnalyticsEvent(
            EventName.WS_NODE_CONNECTED,
            {"node_id": node.uid, "node_version": node_info.version},
        ),
    )

    connect_time = time.time()
    await node_repository.set_node_active_status(node.uid, True)
    if not node_repository.register_node(node):
        # TODO change the code later to WS_1008_POLICY_VIOLATION once we are sure connection retries are not needed
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Node with same node id already connected",
        )
    ping_pong_protocol: PingPongProtocol = protocol_handler.get(
        settings.PING_PONG_PROTOCOL_NAME
    )

    if not ping_pong_protocol.add_node(node_info.name, websocket):
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Node could not be added to the active nodes",
        )
    try:
        while True:
            data = await websocket.receive_text()
            parsed_data = orjson.loads(data)
            if "request_id" in parsed_data:
                request_id = parsed_data["request_id"]
                if request_id is not None:
                    try:
                        await node.request_incoming_queues[request_id].put(parsed_data)
                    except KeyError:
                        logger.error(f"Received chunk for unknown request {request_id}")
                else:
                    logger.error("Invalid request id")
            else:
                # handle protocols
                print("handling_protocols")
                await protocol_handler.handle(parsed_data)
    except orjson.JSONDecodeError:
        await _websocket_error(
            analytics,
            connect_time,
            metrics_queue_repository,
            node,
            node_info,
            node_repository,
            node_uid,
            ping_pong_protocol,
            user,
            analytics_event=EventName.WS_NODE_DISCONNECTED_WITH_ERROR,
            log_message=f"Node {node_uid} disconnected, because of invalid JSON",
        )
    except WebSocketRequestValidationError as e:
        await _websocket_error(
            analytics,
            connect_time,
            metrics_queue_repository,
            node,
            node_info,
            node_repository,
            node_uid,
            ping_pong_protocol,
            user,
            analytics_event=EventName.WS_NODE_DISCONNECTED_WITH_ERROR,
            log_message=f"Node {node_uid} disconnected, because of invalid JSON",
        )
        raise e
    except WebSocketDisconnect:
        await _websocket_error(
            analytics,
            connect_time,
            metrics_queue_repository,
            node,
            node_info,
            node_repository,
            node_uid,
            ping_pong_protocol,
            user,
            analytics_event=EventName.WS_NODE_DISCONNECTED,
            log_message=f"Node {node_uid} disconnected",
        )
    except Exception as e:
        await _websocket_error(
            analytics,
            connect_time,
            metrics_queue_repository,
            node,
            node_info,
            node_repository,
            node_uid,
            ping_pong_protocol,
            user,
            analytics_event=EventName.WS_NODE_DISCONNECTED_WITH_ERROR,
            log_message=f"Node {node_uid} disconnected, because of {e}",
        )
        raise e


async def _websocket_error(
    analytics: Analytics,
    connect_time: float,
    metrics_queue_repository: MetricsQueueRepository,
    node: ConnectedNode,
    node_info: NodeInfo,
    node_repository: NodeRepository,
    node_uid: UUID,
    ping_pong_protocol: PingPongProtocol,
    user: User,
    analytics_event: EventName,
    log_message: str,
):
    await node_repository.set_node_active_status(node.uid, False)
    ping_pong_protocol.remove_node(node_info.name)
    node_repository.deregister_node(node_uid)
    uptime = int(time.time() - connect_time)
    await _increment_uptime(node.uid, uptime, metrics_queue_repository)
    logger.info(log_message)
    analytics.track_event(
        user.uid,
        AnalyticsEvent(analytics_event, {"node_id": node_uid}),
    )


async def _check_before_connecting(
    model_name: Optional[str],
    node_info: NodeInfo,
    benchmark_repository: BenchmarkRepository,
    user: User,
):
    if node_info.is_active:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="A existing connection has already been established",
        )
    if not model_name:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION, reason='No "Model" header provided'
        )
    benchmark = await benchmark_repository.get_node_benchmark(
        user.uid, node_info.node_id, model_name
    )
    if not benchmark:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Benchmarking is not completed",
        )
    if benchmark.tokens_per_second < settings.MINIMUM_COMPLETIONS_TOKENS_PER_SECOND:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Benchmarking performance is too low",
        )


async def _increment_uptime(
    node_id: UUID,
    uptime: int,
    metrics_queue_repository: MetricsQueueRepository,
) -> None:
    node_metrics_increment = NodeMetricsIncrement(node_id=node_id)
    node_metrics_increment.uptime_increment += uptime
    await metrics_queue_repository.push(node_metrics_increment)
