from unittest.mock import AsyncMock

from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.network import get_network_stats_service as service
from distributedinference.service.network.entities import NetworkStatsResponse


async def test_success():
    mock_repository = AsyncMock(spec=NodeRepository)
    mock_repository.get_nodes_count.return_value = 2
    mock_repository.get_connected_nodes_count.return_value = 1
    mock_repository.get_network_throughput.return_value = 321.123
    mock_repository.get_network_throughput_by_model.return_value = {
        "model1": 100.0,
        "model2": 221.123,
    }

    response = await service.execute(mock_repository)
    expected_response = NetworkStatsResponse(
        nodes_count=2,
        connected_nodes_count=1,
        network_throughput=321.123,
        network_throughput_by_model={
            "model1": 100.0,
            "model2": 221.123,
        },
    )
    assert response == expected_response
