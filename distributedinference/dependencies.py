import settings
from distributedinference import api_logger
from distributedinference.analytics.analytics import Analytics
from distributedinference.analytics.posthog import init_posthog
from distributedinference.repository.authentication_api_repository import (
    AuthenticationApiRepository,
)

from distributedinference.repository.connection import get_session_provider
from distributedinference.repository.grafana_api_repository import GrafanaApiRepository
from distributedinference.repository.metrics_queue_repository import (
    MetricsQueueRepository,
)
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.repository.user_repository import UserRepository
from distributedinference.service.node.protocol.protocol_handler import ProtocolHandler

_node_repository_instance: NodeRepository
_metrics_queue_repository: MetricsQueueRepository

_authentication_api_repository: AuthenticationApiRepository
_analytics: Analytics
_protocol_handler: ProtocolHandler

_grafana_api_repository: GrafanaApiRepository


# pylint: disable=W0603
def init_globals():
    # TODO: refactor this, we shoudn't use globals
    global _node_repository_instance
    global _metrics_queue_repository
    global _authentication_api_repository
    global _analytics
    global _protocol_handler
    global _grafana_api_repository
    _node_repository_instance = NodeRepository(
        get_session_provider(), settings.MAX_PARALLEL_REQUESTS_PER_NODE
    )
    _metrics_queue_repository = MetricsQueueRepository()

    _analytics = Analytics(
        posthog=init_posthog(
            is_production=settings.is_production(),
            is_test=settings.is_test(),
        ),
        logger=api_logger.get(),
    )

    if settings.is_production() or (
        settings.STYTCH_PROJECT_ID and settings.STYTCH_SECRET
    ):
        _authentication_api_repository = AuthenticationApiRepository()

    _protocol_handler = ProtocolHandler()
    if settings.GRAFANA_API_BASE_URL and settings.GRAFANA_API_KEY:
        _grafana_api_repository = GrafanaApiRepository(
            settings.GRAFANA_API_BASE_URL, settings.GRAFANA_API_KEY
        )


def get_node_repository() -> NodeRepository:
    return _node_repository_instance


def get_user_repository() -> UserRepository:
    return UserRepository(get_session_provider())


def get_tokens_repository() -> TokensRepository:
    return TokensRepository(get_session_provider())


def get_metrics_queue_repository() -> MetricsQueueRepository:
    return _metrics_queue_repository


def get_authentication_api_repository() -> AuthenticationApiRepository:
    return _authentication_api_repository


def get_analytics() -> Analytics:
    return _analytics


def get_protocol_handler() -> ProtocolHandler:
    return _protocol_handler


def get_grafana_repository() -> GrafanaApiRepository:
    return _grafana_api_repository
