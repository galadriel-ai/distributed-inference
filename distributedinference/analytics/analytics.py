from enum import Enum
from dataclasses import dataclass
from logging import Logger
from typing import Any, Dict
from uuid import UUID

from posthog import Posthog


class EventName(Enum):
    GET_NODE_INFO = "get_node_info"
    GET_NODE_STATS = "get_node_stats"
    POST_NODE_INFO = "post_node_info"
    GET_NODE_BENCHMARK = "get_node_benchmark"
    POST_NODE_BENCHMARK = "post_node_benchmark"

    GET_NETWORK_STATS = "get_network_stats"

    CHAT_COMPLETIONS = "chat_completions"


@dataclass
class AnalyticsEvent:
    name: EventName
    metadata: Dict[str, Any]


class Analytics:
    def __init__(self, posthog: Posthog, logger: Logger):
        self.posthog = posthog
        self.logger = logger

    def track_event(self, user_id: UUID, event: AnalyticsEvent):
        try:
            self.posthog.capture(user_id, event.name.value, event.metadata)
        except Exception as e:
            self.logger.error(f"Error tracking event: {str(e)}")
