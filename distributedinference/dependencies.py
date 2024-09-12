import settings
from distributedinference.repository.authentication_api_repository import (
    AuthenticationApiRepository,
)

from distributedinference.repository.connection import get_session_provider
from distributedinference.repository.metrics_queue_repository import (
    MetricsQueueRepository,
)
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.repository.user_repository import UserRepository

_node_repository_instance: NodeRepository
_metrics_queue_repository: MetricsQueueRepository

_authentication_api_repository: AuthenticationApiRepository


def init_globals():
    # TODO: refactor this, we shoudn't use globals
    global _node_repository_instance
    global _metrics_queue_repository
    global _authentication_api_repository
    _node_repository_instance = NodeRepository(
        get_session_provider(), settings.MAX_PARALLEL_REQUESTS_PER_NODE
    )
    _metrics_queue_repository = MetricsQueueRepository()
    if settings.is_production() or (settings.STYTCH_PROJECT_ID and settings.STYTCH_SECRET):
        _authentication_api_repository = AuthenticationApiRepository()


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
