import time
from typing import AsyncGenerator
from typing import Optional
from uuid import UUID

from prometheus_client import Gauge
from prometheus_client import Histogram

from openai.types import CompletionUsage

import settings
from distributedinference.analytics.analytics import (
    Analytics,
    AnalyticsEvent,
    EventName,
)
from distributedinference import api_logger
from distributedinference.domain.node import llm_inference_proxy, peer_nodes_forwarding
from distributedinference.domain.node.entities import ConnectedNode
from distributedinference.domain.node.entities import InferenceRequest
from distributedinference.domain.node.entities import InferenceResponse
from distributedinference.domain.node.entities import NodeMetricsIncrement
from distributedinference.domain.node.exceptions import NoAvailableNodesError
from distributedinference.repository.metrics_queue_repository import (
    MetricsQueueRepository,
)
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.repository.tokens_repository import UsageTokens

logger = api_logger.get()

node_time_to_first_token_histogram = Histogram(
    "node_time_to_first_token_histogram",
    "Time to first token histogram in seconds by model and node uid",
    ["model_name", "node_uid"],
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10],
)
llm_fallback_called_gauge = Gauge(
    "llm_fallback_called_gauge",
    "Indicates how many times the llm fallback is called",
    ["model_name"],
)


class InferenceExecutor:

    def __init__(
        self,
        node_repository: NodeRepository,
        tokens_repository: TokensRepository,
        metrics_queue_repository: MetricsQueueRepository,
        analytics: Analytics,
    ):
        self.node_repository = node_repository
        self.tokens_repository = tokens_repository
        self.metrics_queue_repository = metrics_queue_repository
        self.analytics = analytics

        self.metrics_increment = None
        self.is_include_usage: bool = False
        self.usage: Optional[CompletionUsage] = None
        self.request_start_time = None
        self.first_token_time = None
        self.time_elapsed_after_first_token = None
        self.request_successful = False

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
            async for response in peer_nodes_forwarding.execute(api_key, request):
                if not response:
                    # Peer nodes also don't support this model, break and call the fallback solution
                    break
                if response.chunk and not response.chunk.choices:
                    # Last chunk only has usage, no choices - request is finished
                    if is_include_usage:
                        yield response
                    logger.debug("Peer nodes completed this inference!")
                    return
                if response.error:
                    # Peer nodes did the inference but there are errors in the response, raise error and return
                    logger.error(f"Peer nodes inference error: {response.error}")
                    raise NoAvailableNodesError()
                if not is_include_usage:
                    response.chunk.usage = None
                yield response

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
                if response.error:
                    logger.error(f"LLM Inference Proxy error: {response.error}")
                    raise NoAvailableNodesError()
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

        await self.node_repository.send_inference_request(node.uid, request)
        self._initialise_metrics(request, node)
        try:
            while True:
                response, is_finished = await self._get_chunk(node, request)
                if response:
                    yield response
                if is_finished:
                    break
        finally:
            await self.node_repository.cleanup_request(node.uid, request.id)
            await self._log_metrics(user_uid, request, node)

    async def _get_chunk(
        self, node: ConnectedNode, request: InferenceRequest
    ) -> (Optional[InferenceResponse], bool):  # type: ignore
        """
        Returns
        * InferenceResponse if there is one
        * bool indicating if the streaming has been finished
        """
        response = await self.node_repository.receive_for_request(node.uid, request.id)
        if not response:
            # Nothing to check, we can mark node as unhealthy and break
            await self._mark_node_as_unhealthy(node)
            return None, True
        self._track_first_token_time()
        if response.chunk:
            # overwriting the usage each time
            self.usage = response.chunk.usage if response.chunk else None
            if self.usage and not response.chunk.choices:
                # last chunk only has usage, no choices - request is finished
                self.request_successful = True
                if self.is_include_usage:
                    return response, True
                self._track_time_elapsed_after_first_token()
                return None, True
            # if users doesn't need usage, we can remove it from the response
            if not self.is_include_usage:
                response.chunk.usage = None
            return response, False

        # if we got an error or no chunk, we can mark node as unhealthy and break
        await self._mark_node_as_unhealthy(node)
        return response, True

    def _initialise_metrics(self, request: InferenceRequest, node: ConnectedNode):
        self.metrics_increment = NodeMetricsIncrement(
            node_id=node.uid, model=node.model
        )
        self.metrics_increment.requests_served_incerement += 1
        self.is_include_usage: bool = bool(
            (request.chat_request.get("stream_options") or {}).get("include_usage")
        ) or not bool(request.chat_request.get("stream"))
        self.request_start_time = time.time()

    def _track_first_token_time(self):
        if not self.first_token_time:
            self.first_token_time = time.time() - self.request_start_time

    def _track_time_elapsed_after_first_token(self):
        # calculate the inference time starting from the first token arrival
        if self.first_token_time:
            self.time_elapsed_after_first_token = (
                time.time() - self.request_start_time - self.first_token_time
            )

    def _select_node(
        self,
        user_uid: UUID,
        request: InferenceRequest,
    ) -> Optional[ConnectedNode]:
        node = self.node_repository.select_node(request.model)
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
        if self.first_token_time is not None:
            self.metrics_increment.time_to_first_token = self.first_token_time
            # add TTFT in histogram
            node_time_to_first_token_histogram.labels(request.model, node.uid).observe(
                self.first_token_time
            )
        # use completion tokens / time elapsed to focus on the model generation performance
        if self.time_elapsed_after_first_token and self.usage:
            self.metrics_increment.inference_tokens_per_second = (
                self.usage.completion_tokens / self.time_elapsed_after_first_token
            )
            logger.debug(
                f"Inference generates {self.usage.completion_tokens} tokens, and takes {self.time_elapsed_after_first_token}s. TPS: {self.metrics_increment.inference_tokens_per_second} TTFT: {self.first_token_time}"
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
        # TODO: in the background?
        await self.tokens_repository.insert_usage_tokens(
            UsageTokens(
                consumer_user_profile_id=user_uid,
                producer_node_info_id=node_uid,
                model_name=request.model,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
            )
        )

    async def _mark_node_as_unhealthy(self, node: ConnectedNode) -> None:
        await self.node_repository.update_node_health_status(node.uid, False)
        self.analytics.track_event(
            node.user_id,
            AnalyticsEvent(
                EventName.NODE_HEALTH,
                {"node_id": node.uid, "is_healthy": False},
            ),
        )
