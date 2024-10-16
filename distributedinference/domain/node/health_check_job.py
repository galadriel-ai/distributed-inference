import asyncio

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
from distributedinference.domain.node.entities import InferenceError
from distributedinference.domain.node.entities import InferenceStatusCodes
from distributedinference.domain.node.entities import InferenceRequest
from distributedinference.domain.node.entities import CheckHealthResponse

from distributedinference.repository.node_repository import ConnectedNode
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.completions.entities import Message

logger = api_logger.get()


async def execute(
    node_repository: NodeRepository,
    analytics: Analytics,
) -> None:
    timeout = settings.HEALTH_CHECK_JOB_TIMEOUT_BETWEEN_RUNS_SECONDS
    while True:
        await asyncio.sleep(timeout)
        logger.debug("Running health check job!")
        try:
            nodes = node_repository.get_unhealthy_nodes()
        except Exception:
            logger.error(
                f"Failed to get unhealthy nodes, restarting in {timeout} seconds",
                exc_info=True,
            )
            continue
        for node in nodes:
            await _check_node_health(node, node_repository, analytics)


async def _check_node_health(
    node: ConnectedNode, node_repository: NodeRepository, analytics: Analytics
) -> None:
    is_healthy = False
    try:
        response = await _send_health_check_inference(node, node_repository)
        logger.debug(
            f"Node health check result, node_id={node.uid}, is_healthy={response.is_healthy}"
        )
        is_healthy = response.is_healthy
        await node_repository.update_node_health_status(node.uid, response.is_healthy)

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


# pylint: disable=R0912, R0913
async def _send_health_check_inference(
    node: ConnectedNode,
    node_repository: NodeRepository,
) -> CheckHealthResponse:
    request = InferenceRequest(
        id=str(uuid7()),
        model=node.model,
        chat_request=await _get_health_check_request(node),
    )
    await node_repository.send_inference_request(node.uid, request)
    try:
        while True:
            response = await node_repository.receive_for_request(node.uid, request.id)
            if not response:
                return CheckHealthResponse(
                    node_id=node.uid,
                    is_healthy=False,
                    error=InferenceError(
                        status_code=InferenceStatusCodes.INTERNAL_SERVER_ERROR,
                        message="Node did not respond to health check request",
                    ),
                )
            if response.chunk and response.chunk.usage and not response.chunk.choices:
                return CheckHealthResponse(
                    node_id=node.uid,
                    is_healthy=True,
                    error=None,
                )
            if response.error:
                return CheckHealthResponse(
                    node_id=node.uid,
                    is_healthy=False,
                    error=response.error,
                )
    finally:
        await node_repository.cleanup_request(node.uid, request.id)


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
