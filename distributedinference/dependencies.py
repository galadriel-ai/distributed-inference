from distributedinference.repository.node_repository import NodeRepository

node_repository_instance = NodeRepository()


def get_node_repository() -> NodeRepository:
    return node_repository_instance
