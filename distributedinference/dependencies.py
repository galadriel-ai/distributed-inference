import settings


from distributedinference.repository.connection import get_session_provider
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.repository.user_repository import UserRepository

_node_repository_instance: NodeRepository


def init_globals():
    # TODO: refactor this, we shoudn't use globals
    global _node_repository_instance
    _node_repository_instance = NodeRepository(
        get_session_provider(), settings.MAX_PARALLEL_REQUESTS_PER_NODE
    )


def get_node_repository() -> NodeRepository:
    return _node_repository_instance


def get_tokens_repository() -> TokensRepository:
    return TokensRepository(get_session_provider())


def get_user_repository() -> UserRepository:
    return UserRepository(get_session_provider())
