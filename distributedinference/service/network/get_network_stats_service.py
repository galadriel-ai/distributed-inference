from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.network.entities import NetworkStatsResponse


async def execute(repository: NodeRepository) -> NetworkStatsResponse:
    nodes_count = await repository.get_nodes_count()
    connected_nodes_count = repository.get_connected_nodes_count()
    throughput = 0
    if connected_nodes_count:
        throughput = await repository.get_network_throughput()
    return NetworkStatsResponse(
        nodes_count=nodes_count,
        connected_nodes_count=connected_nodes_count,
        network_throughput=throughput,
    )
