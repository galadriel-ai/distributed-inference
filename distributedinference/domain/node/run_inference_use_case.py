from typing import AsyncGenerator
from typing import Optional
from uuid import UUID

from openai.types import CompletionUsage
from prometheus_client import Gauge
from prometheus_client import Histogram

import settings
from distributedinference import api_logger
from distributedinference.analytics.analytics import Analytics
from distributedinference.analytics.analytics import AnalyticsEvent
from distributedinference.analytics.analytics import EventName
from distributedinference.domain.node import is_inference_request_finished
from distributedinference.domain.node import is_node_performant
from distributedinference.domain.node import llm_inference_proxy
from distributedinference.domain.node import node_status_transition
from distributedinference.domain.node import peer_nodes_forwarding
from distributedinference.domain.node import select_node_use_case
from distributedinference.domain.node import update_node_status_use_case
from distributedinference.domain.node.entities import ConnectedNode
from distributedinference.domain.node.entities import InferenceErrorStatusCodes
from distributedinference.domain.node.entities import InferenceRequest
from distributedinference.domain.node.entities import InferenceResponse
from distributedinference.domain.node.entities import InferenceStatusCodes
from distributedinference.domain.node.entities import NodeMetricsIncrement
from distributedinference.domain.node.exceptions import NoAvailableNodesError
from distributedinference.domain.node.node_status_transition import NodeStatusEvent
from distributedinference.domain.node.time_tracker import TimeTracker
from distributedinference.repository.connected_node_repository import (
    ConnectedNodeRepository,
)
from distributedinference.repository.metrics_queue_repository import (
    MetricsQueueRepository,
)
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.tokens_repository import (
    DailyUserModelUsageIncrement,
)
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.repository.tokens_repository import UsageTokens
from distributedinference.repository.tokens_queue_repository import (
    TokensQueueRepository,
)

logger = api_logger.get()

node_time_to_first_token_histogram = Histogram(
    "node_time_to_first_token_histogram",
    "Time to first token histogram in seconds by model and node uid",
    ["model_name", "node_uid", "node_status"],
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10],
)
llm_fallback_called_gauge = Gauge(
    "llm_fallback_called_gauge",
    "Indicates how many times the llm fallback is called",
    ["model_name"],
)


class InferenceExecutor:
    metrics_increment: NodeMetricsIncrement

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        node_repository: NodeRepository,
        connected_node_repository: ConnectedNodeRepository,
        tokens_repository: TokensRepository,
        metrics_queue_repository: MetricsQueueRepository,
        tokens_queue_repository: TokensQueueRepository,
        analytics: Analytics,
    ):
        self.node_repository = node_repository
        self.connected_node_repository = connected_node_repository
        self.tokens_repository = tokens_repository
        self.metrics_queue_repository = metrics_queue_repository
        self.tokens_queue_repository = tokens_queue_repository
        self.analytics = analytics

        self.is_include_usage: bool = False
        self.usage: Optional[CompletionUsage] = None
        self.request_successful = False

        self.is_node_marked_as_unhealthy = False
        self.time_tracker = TimeTracker()

    # pylint: disable=too-many-branches, R0912, R0915
    async def execute(
        self,
        user_uid: UUID,
        api_key: str,
        forwarding_from: Optional[str],
        request: InferenceRequest,
    ) -> AsyncGenerator[InferenceResponse, None]:
        node = self._select_node(user_uid=user_uid, request=request)
        if forwarding_from:
            logger.debug(f"Received forwarding call from peer node {forwarding_from}")
        if not node:
            if forwarding_from:
                # Fail early if this is a forwarding request from peers
                logger.error(
                    "No resources to serve the forwarding call, respond with error!"
                )
                raise NoAvailableNodesError()
            # Check if usage is requested
            is_include_usage: bool = bool(
                (request.chat_request.get("stream_options") or {}).get("include_usage")
            ) or not bool(request.chat_request.get("stream"))
            # Forward requests to peer nodes
            logger.info(
                "No node for the requested model available, forwarding to peer nodes!"
            )
            usage = None
            async for response in peer_nodes_forwarding.execute(api_key, request):
                if not response:
                    # Peer nodes also don't support this model, break and call the fallback solution
                    break
                if response.chunk:
                    usage = response.chunk.usage
                    if not is_include_usage:
                        response.chunk.usage = None
                    yield response
                if response.error:
                    # Peer nodes did the inference but there are errors in the response. Return so the error is handled higher
                    logger.error(f"Peer nodes inference error: {response.error}")
                    yield response
                    return
            if usage:
                # Peer nodes did the inference, exit
                logger.debug("Peer nodes completed this inference!")
                return
            llm_fallback_called_gauge.labels(request.model).inc()
            logger.info(
                "Peer nodes don't support this model, calling a fallback proxy!"
            )
            node_uid = settings.GALADRIEL_NODE_INFO_ID
            usage = None
            async for response in llm_inference_proxy.execute(request, node_uid):
                if not response:
                    raise NoAvailableNodesError()

                if response.chunk:
                    usage = response.chunk.usage if response.chunk else None
                    if usage and not response.chunk.choices and not is_include_usage:
                        # Last chunk but usage is not requested - skip the last chunk
                        break
                    if not is_include_usage:
                        response.chunk.usage = None
                yield response
            if usage:
                await self._save_usage(
                    user_uid=user_uid,
                    request=request,
                    usage=usage,
                    node_uid=node_uid,
                )
            return

        await self.connected_node_repository.send_inference_request(node.uid, request)
        self._initialise_metrics(request, node)
        try:
            while True:
                response, is_finished = await self._get_chunk(node, request)
                if response:
                    yield response
                if is_finished:
                    break

            is_performant = is_node_performant.execute(
                self.time_tracker.get_time_to_first_token(),
                self.time_tracker.get_throughput(),
                self.time_tracker.get_prompt_tokens(),
                request.model,
                node.uid,
            )
            if not is_performant:
                await self._mark_node_as_unhealthy(node)
        finally:
            self.connected_node_repository.cleanup_request(node.uid, request.id)
            await self._log_metrics(user_uid, request, node)

    async def _get_chunk(
        self, node: ConnectedNode, request: InferenceRequest
    ) -> (Optional[InferenceResponse], bool):  # type: ignore
        """
        Returns
        * InferenceResponse if there is one
        * bool indicating if the streaming has been finished
        """
        response = await self.connected_node_repository.receive_for_request(
            node.uid, request.id
        )
        if not response:
            # Nothing to check, we can mark node as unhealthy and break
            await self._mark_node_as_unhealthy(node)
            return None, True
        self.time_tracker.chunk_received(response.chunk)
        if response.chunk:
            # overwriting the usage each time
            self.usage = response.chunk.usage if response.chunk else None
            # TODO REFACTOR THIS AFTER ALL NODES ARE UPDATED
            if is_inference_request_finished.execute(node, response, self.usage):
                # last chunk only has usage, no choices - request is finished
                self.request_successful = True
                if not self.is_include_usage:
                    response.chunk.usage = None
                return response, True
            # if users doesn't need usage, we can remove it from the response
            if not self.is_include_usage:
                response.chunk.usage = None
            return response, False
        if response.status == InferenceStatusCodes.ERROR:
            # if we got an error, we can mark node as unhealthy and break
            await self._mark_node_as_unhealthy(node)
            return response, True
        if response.status == InferenceStatusCodes.DONE:
            self.request_successful = True
            return response, True
        # if we got an error or no chunk, we can mark node as unhealthy and break
        if not (
            response.error
            # On client side issues don't blame the node
            and response.error.status_code == InferenceErrorStatusCodes.BAD_REQUEST
        ):
            await self._mark_node_as_unhealthy(node)
        return response, True

    def _initialise_metrics(self, request: InferenceRequest, node: ConnectedNode):
        self.metrics_increment = NodeMetricsIncrement(
            node_id=node.uid, model=node.model
        )
        self.metrics_increment.requests_served_incerement += 1
        self.is_include_usage = bool(
            (request.chat_request.get("stream_options") or {}).get("include_usage")
        ) or not bool(request.chat_request.get("stream"))
        self.time_tracker.start()

    def _select_node(
        self,
        user_uid: UUID,
        request: InferenceRequest,
    ) -> Optional[ConnectedNode]:
        node = select_node_use_case.execute(
            request.model, self.connected_node_repository
        )
        if not node:
            return None

        self.analytics.track_event(
            user_uid,
            AnalyticsEvent(
                EventName.USER_EXECUTED_INFERENCE_REQUEST,
                {"node_id": node.uid, "model": request.model},
            ),
        )
        self.analytics.track_event(
            node.user_id,
            AnalyticsEvent(
                EventName.USER_NODE_SELECTED_FOR_INFERENCE,
                {"node_id": node.uid, "model": request.model},
            ),
        )
        return node

    async def _log_metrics(
        self, user_uid: UUID, request: InferenceRequest, node: ConnectedNode
    ):
        if self.usage:
            await self._save_usage(
                user_uid=user_uid, request=request, node_uid=node.uid, usage=self.usage
            )
        # set only if we got at least one token
        ttft = self.time_tracker.get_time_to_first_token()
        if ttft is not None:
            self.metrics_increment.time_to_first_token = ttft
            # add TTFT in histogram
            node_time_to_first_token_histogram.labels(
                request.model, node.uid, node.node_status.value
            ).observe(ttft)
        # use completion tokens / time elapsed to focus on the model generation performance
        throughput = self.time_tracker.get_throughput()
        if throughput:
            self.metrics_increment.inference_tokens_per_second = throughput
            logger.debug(
                f"Inference generates {self.usage.completion_tokens if self.usage else 0} tokens, and takes {self.time_tracker.get_total_time()}s. TPS: {throughput} TTFT: {self.time_tracker.get_time_to_first_token()}"
            )
        if self.request_successful:
            self.metrics_increment.requests_successful_incerement += 1
        else:
            self.metrics_increment.requests_failed_increment += 1
        await self.metrics_queue_repository.push(self.metrics_increment)

    async def _save_usage(
        self,
        user_uid: UUID,
        request: InferenceRequest,
        node_uid: UUID,
        usage: CompletionUsage,
    ):
        await self.tokens_queue_repository.push_token_usage(
            UsageTokens(
                consumer_user_profile_id=user_uid,
                producer_node_info_id=node_uid,
                model_name=request.model,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
            )
        )
        await self.tokens_queue_repository.push_daily_usage(
            DailyUserModelUsageIncrement(
                user_profile_id=user_uid,
                model_name=request.model,
                tokens_count=usage.total_tokens,
                requests_count=1,
            )
        )

    async def _mark_node_as_unhealthy(self, node: ConnectedNode) -> None:
        if not self.is_node_marked_as_unhealthy:
            self.is_node_marked_as_unhealthy = True
            status = await node_status_transition.execute(
                self.node_repository, node.uid, NodeStatusEvent.DEGRADED
            )
            await update_node_status_use_case.execute(
                node.uid, status, self.node_repository, self.connected_node_repository
            )
            self.analytics.track_event(
                node.user_id,
                AnalyticsEvent(
                    EventName.NODE_HEALTH,
                    {"node_id": node.uid, "is_healthy": False},
                ),
            )
