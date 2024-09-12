from unittest.mock import AsyncMock

from distributedinference.repository.node_repository import NodeRepository, ModelStats
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.service.network import get_network_stats_service as service
from distributedinference.service.network.entities import (
    NetworkStatsResponse,
    NetworkModelStats,
)


async def test_success():
    mock_repository = AsyncMock(spec=NodeRepository)
    mock_repository.get_nodes_count.return_value = 2
    mock_repository.get_connected_nodes_count.return_value = 1
    mock_repository.get_network_throughput.return_value = 321.123
    mock_repository.get_network_model_stats.return_value = [
        ModelStats(model_name="model1", throughput=100.0),
        ModelStats(model_name="model2", throughput=221.123),
    ]

    mock_tokens_repository = AsyncMock(spec=TokensRepository)
    mock_tokens_repository.get_latest_count_by_time.return_value = 1337

    response = await service.execute(mock_repository, mock_tokens_repository)
    expected_response = NetworkStatsResponse(
        nodes_count=2,
        connected_nodes_count=1,
        network_throughput="321.123 tps",
        network_models_stats=[
            NetworkModelStats(model_name="model1", throughput="100.0 tps"),
            NetworkModelStats(model_name="model2", throughput="221.123 tps"),
        ],
        inference_count_day=1337,
    )
    assert response == expected_response
