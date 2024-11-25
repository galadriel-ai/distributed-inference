from datetime import datetime
from unittest.mock import AsyncMock
from uuid import UUID

from uuid_extensions import uuid7

from distributedinference.domain.node.entities import FullNodeInfo
from distributedinference.domain.node.entities import NodeBenchmark
from distributedinference.domain.node.entities import NodeSpecs
from distributedinference.repository.benchmark_repository import BenchmarkRepository
from distributedinference.service.node import save_node_benchmark_service as service
from distributedinference.service.node.entities import PostNodeBenchmarkRequest
from distributedinference.service.node.entities import PostNodeBenchmarkResponse

NODE_UUID = UUID("40c95432-8b2c-4208-bdf4-84f49ff957a3")


def _get_node_info() -> FullNodeInfo:
    return FullNodeInfo(
        node_id=NODE_UUID,
        name="name",
        name_alias="name_alias",
        created_at=datetime(2024, 1, 2),
        specs=NodeSpecs(
            gpu_model="NVIDIA GeForce RTX 4090",
            vram=8,
            gpu_count=2,
            cpu_model="Intel i7",
            cpu_count=4,
            ram=16,
            network_download_speed=1000,
            network_upload_speed=1000,
            operating_system="Linux",
        ),
    )


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
        benchmark_tokens_per_second=request.tokens_per_second,
        gpu_model="NVIDIA GeForce RTX 4090",
        gpu_count=2,
    )

    benchmark_repository = AsyncMock(spec=BenchmarkRepository)
    response = await service.execute(
        request, _get_node_info(), user_id, benchmark_repository
    )
    benchmark_repository.save_node_benchmark.assert_called_once_with(
        user_id, expected_node_info
    )

    assert response == PostNodeBenchmarkResponse(response="OK")
