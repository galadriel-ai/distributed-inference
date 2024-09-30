from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.service.network.entities import (
    NetworkStatsResponse,
    NetworkModelStats,
)


async def execute(
    repository: NodeRepository,
    tokens_repository: TokensRepository,
) -> NetworkStatsResponse:
    nodes_count = await repository.get_nodes_count()
    connected_nodes_count = await repository.get_connected_nodes_count()
    throughput = 0
    network_models_stats = []
    if connected_nodes_count:
        throughput = await repository.get_network_throughput()
        network_models_stats = await repository.get_network_model_stats()

    formatted_throughput = format_tps(throughput)
    formatted_throughput_by_model = [
        NetworkModelStats(
            model_name=stats.model_name, throughput=format_tps(stats.throughput)
        )
        for stats in network_models_stats
    ]

    return NetworkStatsResponse(
        nodes_count=nodes_count,
        connected_nodes_count=connected_nodes_count,
        network_throughput=formatted_throughput,
        inference_count_day=await tokens_repository.get_latest_count_by_time(),
        network_models_stats=formatted_throughput_by_model,
    )


def format_tps(tps: float) -> str:
    if tps.is_integer():
        return f"{tps:.1f} tps"
    return f"{tps:.3f} tps"
