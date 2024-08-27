from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.user_repository import UserRepository

_node_repository_instance = NodeRepository()
_user_repository = UserRepository()


def get_node_repository() -> NodeRepository:
    return _node_repository_instance


def get_user_repository() -> UserRepository:
    return _user_repository
