import settings
from distributedinference.repository.metrics_queue_repository import (
    MetricsQueueRepository,
)

from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.repository.user_repository import UserRepository

_node_repository_instance = NodeRepository(settings.MAX_PARALLEL_REQUESTS_PER_NODE)
_user_repository = UserRepository()
_tokens_repository = TokensRepository()

_metrics_queue_repository = MetricsQueueRepository()


def get_node_repository() -> NodeRepository:
    return _node_repository_instance


def get_user_repository() -> UserRepository:
    return _user_repository


def get_tokens_repository() -> TokensRepository:
    return _tokens_repository


def get_metrics_queue_repository() -> MetricsQueueRepository:
    return _metrics_queue_repository
