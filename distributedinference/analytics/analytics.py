from dataclasses import dataclass
from enum import Enum
from logging import Logger
from typing import Any
from typing import Dict
from typing import Optional
from uuid import UUID

from posthog import Posthog

from distributedinference.domain.user.entities import User


class EventName(Enum):
    # Node
    GET_NODE_INFO = "get_node_info"
    GET_NODE_STATS = "get_node_stats"
    POST_NODE_INFO = "post_node_info"
    GET_NODE_BENCHMARK = "get_node_benchmark"
    POST_NODE_BENCHMARK = "post_node_benchmark"

    GET_NETWORK_STATS = "get_network_stats"

    CHAT_COMPLETIONS = "chat_completions"
    DASHBOARD_CHAT_COMPLETIONS = "dashboard_chat_completions"

    USER_EXECUTED_INFERENCE_REQUEST = "user_executed_inference_request"
    USER_NODE_SELECTED_FOR_INFERENCE = "user_node_selected_for_inference"

    WS_NODE_CONNECTED = "ws_node_connected"
    WS_NODE_DISCONNECTED = "ws_node_disconnected"
    WS_NODE_DISCONNECTED_WITH_ERROR = "ws_node_disconnected_with_error"

    # Dashboard
    SIGNUP = "signup"
    LOGIN = "login"
    SET_PROFILE_DATA = "set_profile_data"
    SET_USER_PASSWORD = "set_user_password"
    CREATE_API_KEY = "create_api_key"
    DELETE_API_KEY = "delete_api_key"
    CREATE_NODE = "create_node"
    UPDATE_NODE = "update_node"

    # API call responses
    API_RESPONSE = "api_response"


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

    def identify_user(self, user: User, profile_data: Optional[Dict] = None):
        try:
            self.posthog.identify(
                user.uid,
                {"email": user.email, "profile_data": profile_data or {}},
                disable_geoip=True,
            )
        except Exception as e:
            self.logger.error(f"Error identifying user: {str(e)}")
