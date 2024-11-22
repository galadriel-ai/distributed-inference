from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from uuid_extensions import uuid7

from distributedinference.domain.node.entities import NodeBenchmark
from distributedinference.domain.node.entities import NodeInfo
from distributedinference.domain.node.entities import NodeSpecs
from distributedinference.domain.user.entities import User
from distributedinference.repository.benchmark_repository import BenchmarkRepository
from distributedinference.service import error_responses
from distributedinference.service.node import get_node_benchmark_service as service
from distributedinference.service.node.entities import GetNodeBenchmarkResponse

NODE_UUID = UUID("40c95432-8b2c-4208-bdf4-84f49ff957a3")
NODE_INFO = NodeInfo(
    node_id=NODE_UUID,
    name="name",
    name_alias="name_alias",
    created_at=None,
    specs=NodeSpecs(
        cpu_model="mock_cpu_model",
        cpu_count=1,
        gpu_model="mock_gpu_model",
        vram=2,
        ram=3,
        network_download_speed=100,
        network_upload_speed=50,
        operating_system="mock_operating_system",
        gpu_count=1,
        version=None,
    ),
)


async def test_execute_success():
    model_name = "mock_model"
    node_benchmark = NodeBenchmark(
        node_id=NODE_UUID,
        model_name=model_name,
        benchmark_tokens_per_second=123.45,
        gpu_model="NVIDIA GeForce RTX 4090",
    )
    expected_response = GetNodeBenchmarkResponse(
        node_id=str(NODE_UUID),
        model_name=node_benchmark.model_name,
        tokens_per_second=node_benchmark.benchmark_tokens_per_second,
    )
    user = User(
        uid=uuid7(),
        name="John Doe",
        email="johndoe@mail.com",
        usage_tier_id=UUID("06706644-2409-7efd-8000-3371c5d632d3"),
    )

    mock_repository = AsyncMock(spec=BenchmarkRepository)
    mock_repository.get_node_benchmark.return_value = node_benchmark
    response = await service.execute(user, NODE_INFO, model_name, mock_repository)
    mock_repository.get_node_benchmark.assert_called_once_with(
        user.uid, NODE_UUID, model_name
    )

    assert response == expected_response


async def test_execute_not_found():
    user = User(
        uid=uuid7(),
        name="John Doe",
        email="johndoe@mail.com",
        usage_tier_id=UUID("06706644-2409-7efd-8000-3371c5d632d3"),
    )

    mock_repository = AsyncMock(spec=BenchmarkRepository)
    mock_repository.get_node_benchmark.return_value = None

    with pytest.raises(error_responses.NotFoundAPIError) as e:
        await service.execute(user, NODE_INFO, "model_name", mock_repository)
        assert e is not None
