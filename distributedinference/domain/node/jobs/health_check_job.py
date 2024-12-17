import asyncio
from typing import List
from typing import cast

from uuid_extensions import uuid7
from openai._utils import async_maybe_transform
from openai.types.chat import CompletionCreateParams

import settings

from distributedinference.analytics.analytics import (
    Analytics,
    AnalyticsEvent,
    EventName,
)
from distributedinference.api_logger import api_logger
from distributedinference.domain.node import is_node_performant
from distributedinference.domain.node import node_status_transition
from distributedinference.domain.node import is_inference_request_finished
from distributedinference.domain.node import update_node_status_use_case
from distributedinference.domain.node.entities import InferenceError
from distributedinference.domain.node.entities import InferenceStatusCodes
from distributedinference.domain.node.entities import InferenceErrorStatusCodes
from distributedinference.domain.node.entities import InferenceRequest
from distributedinference.domain.node.entities import CheckHealthResponse
from distributedinference.domain.node.entities import NodeStatus
from distributedinference.domain.node.node_status_transition import NodeStatusEvent
from distributedinference.domain.node.time_tracker import TimeTracker
from distributedinference.repository.connected_node_repository import (
    ConnectedNodeRepository,
)

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
    connected_node_repository: ConnectedNodeRepository,
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
        # 1. Connection checks for all nodes that are shown as connected to the current backend
        await _check_connected_nodes_consistency(
            connected_node_repository, node_repository
        )

        # 2. Benchmarking checks for all nodes that are unhealthy or in RUNNING_BENCHMARKING state
        nodes = await _get_nodes_for_check(node_repository, connected_node_repository)
        for node in nodes:
            await _check_node_health(
                node,
                node_repository,
                connected_node_repository,
                analytics,
                protocol_handler,
            )


async def _get_nodes_for_check(
    node_repository: NodeRepository,
    connected_node_repository: ConnectedNodeRepository,
) -> List[ConnectedNode]:
    connected_nodes = connected_node_repository.get_locally_connected_nodes()
    connected_nodes_running_benchmarking = []
    try:
        connected_nodes_running_benchmarking = (
            await node_repository.get_nodes_for_benchmarking(connected_nodes)
        )
    except Exception:
        logger.error(
            "Failed to get nodes for benchmarking, restarting...", exc_info=True
        )

    unhealthy_nodes = [
        node for node in connected_nodes if not node.node_status.is_healthy()
    ]

    return unhealthy_nodes + connected_nodes_running_benchmarking


async def _send_health_check_inference(
    node: ConnectedNode,
    connected_node_repository: ConnectedNodeRepository,
) -> CheckHealthResponse:
    request = InferenceRequest(
        id=str(uuid7()),
        model=node.model,
        chat_request=await _get_health_check_request(node),
    )
    time_tracker = TimeTracker()
    time_tracker.start()
    await connected_node_repository.send_inference_request(node.uid, request)
    try:
        while True:
            response = await connected_node_repository.receive_for_request(
                node.uid, request.id
            )
            if not response:
                return CheckHealthResponse(
                    node_id=node.uid,
                    is_healthy=False,
                    error=InferenceError(
                        status_code=InferenceErrorStatusCodes.INTERNAL_SERVER_ERROR,
                        message="Node did not respond to health check request",
                    ),
                )
            time_tracker.chunk_received(response.chunk)
            usage = response.chunk.usage if response.chunk else None
            if (
                # TODO remove this after all nodes are updated
                is_inference_request_finished.execute(node, response, usage)
                or response.status == InferenceStatusCodes.DONE
            ):
                is_healthy = is_node_performant.execute(
                    time_tracker.get_time_to_first_token(),
                    time_tracker.get_throughput(),
                    time_tracker.get_prompt_tokens(),
                    request.model,
                    node.uid,
                )
                return CheckHealthResponse(
                    node_id=node.uid,
                    is_healthy=is_healthy,
                    error=None,
                )
            if response.status == InferenceStatusCodes.ERROR:
                return CheckHealthResponse(
                    node_id=node.uid,
                    is_healthy=False,
                    error=response.error,
                )
            if response.error:
                return CheckHealthResponse(
                    node_id=node.uid,
                    is_healthy=False,
                    error=response.error,
                )
            # TODO: what if node returns empty chunks? We should still return something?
            if not response.chunk:
                return CheckHealthResponse(
                    node_id=node.uid,
                    is_healthy=False,
                    error=None,
                )
    finally:
        connected_node_repository.cleanup_request(node.uid, request.id)


# pylint: disable=R0912, R0913
async def _check_node_health(
    node: ConnectedNode,
    node_repository: NodeRepository,
    connected_node_repository: ConnectedNodeRepository,
    analytics: Analytics,
    _: ProtocolHandler,
) -> None:
    is_healthy = False
    try:
        node_status = await node_repository.get_node_status(node.uid)
        if node_status and node_status.is_disabled():
            logger.debug(
                f"Skipping node health check for node_id={node.uid}, current status: {node_status.value}"
            )
            return
        response = await _send_health_check_inference(node, connected_node_repository)
        is_healthy = response.is_healthy
        logger.debug(
            f"Node health check result, node_id={node.uid}, is_healthy={is_healthy}"
        )
        status = NodeStatus.RUNNING
        if not is_healthy:
            status = await node_status_transition.execute(
                node_repository, node.uid, NodeStatusEvent.DEGRADED
            )
        # TODO: add back soon
        # if status == NodeStatus.STOPPED_BENCHMARK_FAILED:
        #     await _disconnect_node(
        #         node,
        #         node_repository,
        #         connected_node_repository,
        #         protocol_handler,
        #         status
        #     )

        await update_node_status_use_case.execute(
            node.uid, status, node_repository, connected_node_repository
        )

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


def _get_long_text():
    file_path = "distributedinference/assets/ai_wiki_8k.txt"
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


async def _get_health_check_request(node: ConnectedNode) -> CompletionCreateParams:
    try:
        long_text = _get_long_text()
        result = await async_maybe_transform(
            {
                "messages": [Message(role="user", content=long_text)],
                "model": node.model,
            },
            CompletionCreateParams,
        )
        return cast(CompletionCreateParams, result)
    except Exception as e:
        logger.warning("Failed to create health check request", exc_info=True)
        raise e


async def _disconnect_node(
    node: ConnectedNode,
    node_repository: NodeRepository,
    connected_node_repository: ConnectedNodeRepository,
    protocol_handler: ProtocolHandler,
    node_status: NodeStatus,
):
    await connected_node_repository.close_node_connection(node.uid)
    connected_node_repository.deregister_node(node.uid)
    await node_repository.update_node_to_disconnected(node.uid, node_status)
    ping_pong_protocol: PingPongProtocol = protocol_handler.get(
        settings.PING_PONG_PROTOCOL_NAME
    )
    health_check_protocol: HealthCheckProtocol = protocol_handler.get(
        HealthCheckProtocol.PROTOCOL_NAME
    )
    await ping_pong_protocol.remove_node_by_uid(node.uid)
    await health_check_protocol.remove_node_by_uid(node.uid)


async def _check_connected_nodes_consistency(
    connected_node_repository: ConnectedNodeRepository, node_repository: NodeRepository
) -> None:
    backend_host = connected_node_repository.get_backend_host()
    if backend_host is None:
        logger.error(
            "Backend host is None! Skipping connected nodes consistency check."
        )
        return None
    connected_nodes_locally = (
        connected_node_repository.get_locally_connected_node_keys()
    )
    connected_nodes_from_db = (
        await node_repository.get_connected_nodes_to_the_current_backend(backend_host)
    )
    for node_uid in connected_nodes_from_db:
        if node_uid not in connected_nodes_locally:
            node_status = await node_status_transition.execute(
                node_repository, node_uid, NodeStatusEvent.STOP
            )
            logger.error(
                f"Node {node_uid} connection is corrupted. Setting state to {node_status} and disconnecting..."
            )
            await node_repository.update_node_to_disconnected(node_uid, node_status)
    return None
