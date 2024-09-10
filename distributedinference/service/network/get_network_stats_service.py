from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.network.entities import NetworkStatsResponse


async def execute(repository: NodeRepository) -> NetworkStatsResponse:
    nodes_count = await repository.get_nodes_count()
    connected_nodes_count = repository.get_connected_nodes_count()
    throughput = 0
    throughput_by_model = {}
    if connected_nodes_count:
        throughput = await repository.get_network_throughput()
        throughput_by_model = await repository.get_network_throughput_by_model()

    formatted_throughput = format_tps(throughput)
    formatted_throughput_by_model = {
        model: format_tps(tps) for model, tps in throughput_by_model.items()
    }

    return NetworkStatsResponse(
        nodes_count=nodes_count,
        connected_nodes_count=connected_nodes_count,
        network_throughput=formatted_throughput,
        network_throughput_by_model=formatted_throughput_by_model,
    )


def format_tps(tps: float) -> str:
    return f"{tps:.3f} tps"
