import asyncio
from typing import List

from uuid_extensions import uuid7
from openai._utils import async_maybe_transform
from openai.types.chat import CompletionCreateParams

import settings

from distributedinference.analytics.analytics import (
    Analytics,
    AnalyticsEvent,
    EventName,
)
from distributedinference import api_logger
from distributedinference.domain.node import is_node_healthy
from distributedinference.domain.node import node_status_transition
from distributedinference.domain.node.entities import InferenceError
from distributedinference.domain.node.entities import InferenceStatusCodes
from distributedinference.domain.node.entities import InferenceRequest
from distributedinference.domain.node.entities import CheckHealthResponse
from distributedinference.domain.node.entities import NodeStatus
from distributedinference.domain.node.node_status_transition import NodeStatusEvent
from distributedinference.domain.node.time_tracker import TimeTracker

from distributedinference.repository.node_repository import ConnectedNode
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.completions.entities import Message
from distributedinference.service.node.protocol.health_check.protocol import (
    HealthCheckProtocol,
)
from distributedinference.service.node.protocol.ping_pong_protocol import (
    PingPongProtocol,
)
from distributedinference.service.node.protocol.protocol_handler import ProtocolHandler

logger = api_logger.get()


async def execute(
    node_repository: NodeRepository,
    analytics: Analytics,
    protocol_handler: ProtocolHandler,
) -> None:
    """
    Checks for unhealthy nodes and nodes that are marked as RUNNING_BENCHMARKING.

    Sends actual inference request and checks for the result. If result arrives on time
    and is valid the Node will be marked back again as RUNNING
    """
    timeout = settings.HEALTH_CHECK_JOB_TIMEOUT_BETWEEN_RUNS_SECONDS
    while True:
        await asyncio.sleep(timeout)
        logger.debug("Running health check job!")
        nodes = await _get_nodes_for_check(node_repository)
        for node in nodes:
            await _check_node_health(node, node_repository, analytics, protocol_handler)


async def _get_nodes_for_check(
    node_repository: NodeRepository,
) -> List[ConnectedNode]:
    result = []
    try:
        nodes = node_repository.get_unhealthy_nodes()
        result += nodes
    except Exception:
        logger.error(
            "Failed to get unhealthy nodes, restarting...",
            exc_info=True,
        )

    try:
        nodes = await node_repository.get_nodes_for_benchmarking()
        result += nodes
    except Exception:
        logger.error(
            "Failed to get nodes for benchmarking, restarting...", exc_info=True
        )

    return result


async def _send_health_check_inference(
    node: ConnectedNode,
    node_repository: NodeRepository,
) -> CheckHealthResponse:
    request = InferenceRequest(
        id=str(uuid7()),
        model=node.model,
        chat_request=await _get_health_check_request(node),
    )
    time_tracker = TimeTracker()
    time_tracker.start()
    await node_repository.send_inference_request(node.uid, request)
    try:
        while True:
            response = await node_repository.receive_for_request(node.uid, request.id)
            time_tracker.chunk_received()
            if not response:
                return CheckHealthResponse(
                    node_id=node.uid,
                    is_healthy=False,
                    time_to_first_token=0.0,
                    tokens_per_second=0.0,
                    error=InferenceError(
                        status_code=InferenceStatusCodes.INTERNAL_SERVER_ERROR,
                        message="Node did not respond to health check request",
                    ),
                )
            if response.chunk and response.chunk.usage and not response.chunk.choices:
                time_tracker.track_usage(response.chunk.usage)
                is_healthy = is_node_healthy.execute(
                    time_tracker.get_time_to_first_token(),
                    time_tracker.get_throughput()
                )
                return CheckHealthResponse(
                    node_id=node.uid,
                    is_healthy=is_healthy,
                    time_to_first_token=time_tracker.get_time_to_first_token(),
                    tokens_per_second=time_tracker.get_throughput(),
                    error=None,
                )
            if response.error:
                return CheckHealthResponse(
                    node_id=node.uid,
                    is_healthy=False,
                    time_to_first_token=0.0,
                    tokens_per_second=0.0,
                    error=response.error,
                )
            # TODO: what if node returns empty chunks? We should still return something?
            if not response.chunk:
                return CheckHealthResponse(
                    node_id=node.uid,
                    is_healthy=False,
                    time_to_first_token=0.0,
                    tokens_per_second=0.0,
                    error=None,
                )
    finally:
        await node_repository.cleanup_request(node.uid, request.id)


# pylint: disable=R0912, R0913
async def _check_node_health(
    node: ConnectedNode,
    node_repository: NodeRepository,
    analytics: Analytics,
    protocol_handler: ProtocolHandler,
) -> None:
    is_healthy = False
    try:
        response = await _send_health_check_inference(node, node_repository)
        logger.debug(
            f"Node health check result, node_id={node.uid}, is_healthy={response.is_healthy}"
        )
        is_healthy = response.is_healthy
        status = NodeStatus.RUNNING
        if not is_healthy:
            status = await node_status_transition.execute(
                node_repository, node.uid, NodeStatusEvent.DEGRADED
            )
        if status == NodeStatus.STOPPED_BENCHMARK_FAILED:
            await _disconnect_node(node, node_repository, protocol_handler, status)

        await node_repository.update_node_status(node.uid, is_healthy, status)

    except Exception:
        logger.error(
            f"Failed to check node health, node_id={node.uid}",
            exc_info=True,
        )
    finally:
        analytics.track_event(
            node.user_id,
            AnalyticsEvent(
                EventName.NODE_HEALTH,
                {"node_id": node.uid, "is_healthy": is_healthy},
            ),
        )


async def _get_health_check_request(node: ConnectedNode) -> CompletionCreateParams:
    try:
        return await async_maybe_transform(
            {
                "messages": [
                    Message(role="user", content="Respond with only letter A")
                ],
                "model": node.model,
            },
            CompletionCreateParams,
        )
    except Exception as e:
        logger.warning("Failed to create health check request", exc_info=True)
        raise e


async def _disconnect_node(
    node: ConnectedNode,
    node_repository: NodeRepository,
    protocol_handler: ProtocolHandler,
    node_status: NodeStatus,
):
    await node_repository.close_node_connection(node.uid)
    node_repository.deregister_node(node.uid)
    await node_repository.update_node_to_disconnected(node.uid, node_status)
    ping_pong_protocol: PingPongProtocol = protocol_handler.get(
        settings.PING_PONG_PROTOCOL_NAME
    )
    health_check_protocol: HealthCheckProtocol = protocol_handler.get(
        HealthCheckProtocol.PROTOCOL_NAME
    )
    await ping_pong_protocol.remove_node_by_uid(node.uid)
    await health_check_protocol.remove_node_by_uid(node.uid)
