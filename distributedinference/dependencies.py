import settings

from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.repository.user_repository import UserRepository

_node_repository_instance = NodeRepository(settings.MAX_PARALLEL_REQUESTS_PER_NODE)
_user_repository = UserRepository()
_tokens_repository = TokensRepository()


def get_node_repository() -> NodeRepository:
    return _node_repository_instance


def get_tokens_repository() -> TokensRepository:
    return _tokens_repository


def get_user_repository() -> UserRepository:
    return _user_repository
