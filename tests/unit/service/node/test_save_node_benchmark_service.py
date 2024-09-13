from unittest.mock import AsyncMock
from uuid import UUID

from uuid_extensions import uuid7

from distributedinference.domain.node.entities import NodeBenchmark
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.service.node import save_node_benchmark_service as service
from distributedinference.service.node.entities import PostNodeBenchmarkRequest
from distributedinference.service.node.entities import PostNodeBenchmarkResponse

NODE_UUID = UUID("40c95432-8b2c-4208-bdf4-84f49ff957a3")


async def test_execute_success():
    user_id = uuid7()
    request = PostNodeBenchmarkRequest(
        node_id=str(NODE_UUID),
        model_name="mock_model",
        tokens_per_second=1337.37,
    )

    expected_node_info = NodeBenchmark(
        node_id=NODE_UUID,
        model_name=request.model_name,
        tokens_per_second=request.tokens_per_second,
    )

    mock_repository = AsyncMock(spec=NodeRepository)
    response = await service.execute(request, user_id, mock_repository)
    mock_repository.save_node_benchmark.assert_called_once_with(
        user_id, expected_node_info
    )

    assert response == PostNodeBenchmarkResponse(response="OK")
