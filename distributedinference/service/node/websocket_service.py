import time
from datetime import datetime
from typing import Dict
from typing import Optional
from uuid import UUID

import orjson
from fastapi import WebSocket
from fastapi import WebSocketDisconnect
from fastapi import status
from fastapi.exceptions import WebSocketException
from fastapi.exceptions import WebSocketRequestValidationError
from packaging.version import Version

import settings
from distributedinference import api_logger
from distributedinference.analytics.analytics import Analytics
from distributedinference.analytics.analytics import AnalyticsEvent
from distributedinference.analytics.analytics import EventName
from distributedinference.domain.node import node_status_transition
from distributedinference.domain.node.entities import ConnectedNode, ModelType
from distributedinference.domain.node.entities import FullNodeInfo
from distributedinference.domain.node.entities import NodeMetrics
from distributedinference.domain.node.entities import NodeStatus
from distributedinference.domain.node.node_status_transition import NodeStatusEvent
from distributedinference.domain.user.entities import User
from distributedinference.repository.benchmark_repository import BenchmarkRepository
from distributedinference.repository.connected_node_repository import (
    ConnectedNodeRepository,
)
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.node.protocol.health_check.protocol import (
    HealthCheckProtocol,
)
from distributedinference.service.node.protocol.ping_pong_protocol import (
    PingPongProtocol,
)
from distributedinference.service.node.protocol.protocol_handler import ProtocolHandler

logger = api_logger.get()


# pylint: disable=R0912, R0913, R0914, R0915
async def execute(
    websocket: WebSocket,
    user: User,
    node_info: FullNodeInfo,
    model_name: Optional[str],
    model_type: Optional[str],
    node_repository: NodeRepository,
    connected_node_repository: ConnectedNodeRepository,
    benchmark_repository: BenchmarkRepository,
    analytics: Analytics,
    protocol_handler: ProtocolHandler,
):
    logger.info(
        f"Node with user_id={user.uid}, node_id={node_info.node_id} and model_name={model_name} is trying to connect"
    )
    await websocket.accept()

    backend_host = connected_node_repository.get_backend_host()
    if backend_host is None:
        raise WebSocketException(
            code=status.WS_1011_INTERNAL_ERROR,
            reason="Backend host is not initialized",
        )

    # By default, the model type is LLM to support backward compatibility
    enum_model_type = (
        ModelType.DIFFUSION
        if model_type and model_type.upper() == "DIFFUSION"
        else ModelType.LLM
    )

    await _check_before_connecting(
        model_name,
        enum_model_type,
        node_info,
        node_repository,
        benchmark_repository,
        user,
    )
    formatted_model_name: str = model_name or ""

    node_uid = node_info.node_id
    connect_time = time.time()
    node_status = await node_status_transition.execute(
        node_repository, node_uid, NodeStatusEvent.START, enum_model_type
    )
    await node_repository.set_node_connection_timestamp(
        node_uid,
        formatted_model_name,
        datetime.fromtimestamp(connect_time),
        backend_host,
        node_status,
    )
    node = ConnectedNode(
        uid=node_uid,
        user_id=user.uid,
        model=formatted_model_name,
        model_type=enum_model_type,
        vram=node_info.specs.vram,
        connected_at=int(time.time()),
        connected_host=backend_host,
        websocket=websocket,
        request_incoming_queues={},
        is_self_hosted=user.is_self_hosted_nodes_provider(),
        node_status=node_status,
        version=Version(node_info.specs.version) if node_info.specs.version else None,
    )
    logger.info(f"Node {node_uid} connected")
    analytics.track_event(
        user.uid,
        AnalyticsEvent(
            EventName.WS_NODE_CONNECTED,
            {"node_id": node.uid, "node_version": node_info.specs.version},
        ),
    )

    if not connected_node_repository.register_node(node):
        # TODO change the code later to WS_1008_POLICY_VIOLATION once we are sure connection retries are not needed
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Node with same node id already connected",
        )
    ping_pong_protocol: PingPongProtocol = protocol_handler.get(
        settings.PING_PONG_PROTOCOL_NAME
    )

    if not ping_pong_protocol.add_node(
        node_info.node_id, node_info.name, formatted_model_name
    ):
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Node could not be added to the active nodes",
        )
    health_check_protocol: HealthCheckProtocol = protocol_handler.get(
        HealthCheckProtocol.PROTOCOL_NAME
    )
    # TODO: Skip health check for image generation models
    if node.model_type is ModelType.LLM:
        health_check_protocol.add_node(
            node_info.node_id, node_info.name, node_info.specs.version
        )
    try:
        while True:
            data = await websocket.receive_text()
            parsed_data = orjson.loads(data)
            if "request_id" in parsed_data:
                request_id = parsed_data["request_id"]
                if request_id is not None:
                    await connected_node_repository.add_inference_response_chunk(
                        node.uid, request_id, parsed_data
                    )
                else:
                    logger.error("Invalid request id")
            else:
                # handle protocols
                print("handling_protocols")
                await protocol_handler.handle(parsed_data)
    except orjson.JSONDecodeError:
        await _websocket_error(
            analytics,
            node,
            node_info,
            node_repository,
            connected_node_repository,
            node_uid,
            ping_pong_protocol,
            health_check_protocol,
            user,
            analytics_event=EventName.WS_NODE_DISCONNECTED_WITH_ERROR,
            log_message=f"Node {node_uid} disconnected, because of invalid JSON",
        )
    except WebSocketRequestValidationError as e:
        await _websocket_error(
            analytics,
            node,
            node_info,
            node_repository,
            connected_node_repository,
            node_uid,
            ping_pong_protocol,
            health_check_protocol,
            user,
            analytics_event=EventName.WS_NODE_DISCONNECTED_WITH_ERROR,
            log_message=f"Node {node_uid} disconnected, because of invalid JSON",
        )
        raise e
    except WebSocketDisconnect:
        await _websocket_error(
            analytics,
            node,
            node_info,
            node_repository,
            connected_node_repository,
            node_uid,
            ping_pong_protocol,
            health_check_protocol,
            user,
            analytics_event=EventName.WS_NODE_DISCONNECTED,
            log_message=f"Node {node_uid} disconnected",
        )
    except Exception as e:
        await _websocket_error(
            analytics,
            node,
            node_info,
            node_repository,
            connected_node_repository,
            node_uid,
            ping_pong_protocol,
            health_check_protocol,
            user,
            analytics_event=EventName.WS_NODE_DISCONNECTED_WITH_ERROR,
            log_message=f"Node {node_uid} disconnected, because of {e}",
        )
        raise e


async def _websocket_error(
    analytics: Analytics,
    node: ConnectedNode,
    node_info: FullNodeInfo,
    node_repository: NodeRepository,
    connected_node_repository: ConnectedNodeRepository,
    node_uid: UUID,
    ping_pong_protocol: PingPongProtocol,
    health_check_protocol: HealthCheckProtocol,
    user: User,
    analytics_event: EventName,
    log_message: str,
):
    await ping_pong_protocol.remove_node(node_info.name)
    await health_check_protocol.remove_node(node_info.name)
    node_status = await _get_new_node_stopped_status(node.uid, node_repository)
    await node_repository.update_node_to_disconnected(node.uid, node_status)

    connected_node_repository.deregister_node(node_uid)
    logger.info(f"{log_message}, status: {node_status}")
    analytics.track_event(
        user.uid,
        AnalyticsEvent(analytics_event, {"node_id": node_uid}),
    )


async def _get_new_node_stopped_status(
    node_id: UUID, node_repository: NodeRepository
) -> NodeStatus:
    return await node_status_transition.execute(
        node_repository, node_id, NodeStatusEvent.STOP
    )


async def _check_before_connecting(
    model_name: Optional[str],
    enum_model_type: ModelType,
    node_info: FullNodeInfo,
    node_repository: NodeRepository,
    benchmark_repository: BenchmarkRepository,
    user: User,
):
    node_metrics: Dict[UUID, NodeMetrics] = (
        await node_repository.get_node_metrics_by_ids([node_info.node_id])
    )
    if (
        node_metrics.get(node_info.node_id)
        and node_metrics[node_info.node_id].status.is_connected()
    ):
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="A existing connection has already been established",
        )
    # Skip benchmarking check for diffusion models
    if enum_model_type is ModelType.DIFFUSION:
        return

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
    min_tokens_sec = settings.MINIMUM_COMPLETIONS_TOKENS_PER_SECOND_PER_MODEL.get(
        model_name, settings.MINIMUM_COMPLETIONS_TOKENS_PER_SECOND
    )
    if benchmark.benchmark_tokens_per_second < min_tokens_sec:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Benchmarking performance is too low",
        )
